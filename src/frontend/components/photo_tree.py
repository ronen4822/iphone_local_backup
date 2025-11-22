"""Tree view component for photo selection"""
import customtkinter as ctk
from typing import Dict, Optional, Callable
import tkinter as tk
from tkinter import ttk

from ...backend.models import YearStats, MonthStats
from ...core.utils import format_size


class PhotoTreeView(ctk.CTkFrame):
    """Tree view with checkboxes for year/month photo selection"""

    def __init__(self, parent, on_selection_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)

        self.on_selection_changed = on_selection_changed
        self._year_stats: Dict[int, YearStats] = {}
        self._tree_items: Dict[str, str] = {}  # Maps year/month to tree item ID
        self._animation_running = False
        self._spinner_index = 0

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="Select Photos to Export",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(10, 5), padx=10, anchor="w")

        # Loading frame (initially hidden)
        self.loading_frame = ctk.CTkFrame(self)

        self.loading_label = ctk.CTkLabel(
            self.loading_frame,
            text="⠋ Analyzing media...",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.loading_label.pack(pady=100)

        # Create scrollable frame for treeview
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create treeview with scrollbar
        scrollbar = ttk.Scrollbar(self.tree_frame)
        scrollbar.pack(side="right", fill="y")

        # Configure style for dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b",
                        borderwidth=0,
                        font=("TkDefaultFont", 12),
                        rowheight=28)
        style.configure("Treeview.Heading",
                        background="#1f538d",
                        foreground="white",
                        borderwidth=0,
                        font=("TkDefaultFont", 12, "bold"))
        style.map('Treeview', background=[('selected', '#1f538d')])

        # Create treeview
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=("count", "size"),
            selectmode="none",
            yscrollcommand=scrollbar.set
        )
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=self.tree.yview)

        # Configure columns
        self.tree.heading("#0", text="Year / Month")
        self.tree.heading("count", text="Photos")
        self.tree.heading("size", text="Size")

        self.tree.column("#0", width=200, minwidth=150)
        self.tree.column("count", width=80, anchor="center")
        self.tree.column("size", width=100, anchor="e")

        # Bind click event
        self.tree.bind("<Button-1>", self._on_tree_click)

        # Summary label
        self.summary_label = ctk.CTkLabel(
            self,
            text="No photos loaded",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.summary_label.pack(pady=5, padx=10, anchor="w")

    def load_photos(self, year_stats: Dict[int, YearStats]):
        """Load photo statistics into tree view"""
        self._year_stats = year_stats
        self._tree_items.clear()

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add years in descending order
        for year in sorted(year_stats.keys(), reverse=True):
            year_stat = year_stats[year]
            self._add_year_node(year_stat)

        self._update_summary()

    def _add_year_node(self, year_stat: YearStats):
        """Add year node to tree"""
        checkbox = "☐"  # Unchecked
        year_text = f"{checkbox} {year_stat.year}"

        year_item = self.tree.insert(
            "",
            "end",
            text=year_text,
            values=(year_stat.photo_count, format_size(year_stat.total_size)),
            tags=("year",)
        )

        self._tree_items[f"year_{year_stat.year}"] = year_item

        # Add month nodes
        for month in sorted(year_stat.months.keys()):
            month_stat = year_stat.months[month]
            self._add_month_node(year_item, year_stat.year, month_stat)

    def _add_month_node(self, year_item: str, year: int, month_stat: MonthStats):
        """Add month node to tree"""
        checkbox = "☐"  # Unchecked
        month_text = f"{checkbox} {month_stat.month_name}"

        month_item = self.tree.insert(
            year_item,
            "end",
            text=month_text,
            values=(month_stat.photo_count, format_size(month_stat.total_size)),
            tags=("month",)
        )

        self._tree_items[f"month_{year}_{month_stat.month}"] = month_item

    def _on_tree_click(self, event):
        """Handle tree item click"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "tree":
            return

        item = self.tree.identify_row(event.y)
        if not item:
            return

        tags = self.tree.item(item, "tags")

        if "year" in tags:
            self._toggle_year(item)
        elif "month" in tags:
            self._toggle_month(item)

    def _toggle_year(self, item: str):
        """Toggle year selection"""
        # Find the year
        year = None
        for key, value in self._tree_items.items():
            if value == item and key.startswith("year_"):
                year = int(key.split("_")[1])
                break

        if year is None:
            return

        year_stat = self._year_stats[year]
        year_stat.selected = not year_stat.selected

        # Update checkbox
        checkbox = "☑" if year_stat.selected else "☐"
        self.tree.item(item, text=f"{checkbox} {year}")

        # Update all months
        for month_stat in year_stat.months.values():
            month_stat.selected = year_stat.selected
            month_item = self._tree_items.get(f"month_{year}_{month_stat.month}")
            if month_item:
                checkbox = "☑" if month_stat.selected else "☐"
                self.tree.item(month_item, text=f"{checkbox} {month_stat.month_name}")

        self._update_summary()

        if self.on_selection_changed:
            self.on_selection_changed()

    def _toggle_month(self, item: str):
        """Toggle month selection"""
        # Find the month
        year = None
        month = None
        for key, value in self._tree_items.items():
            if value == item and key.startswith("month_"):
                parts = key.split("_")
                year = int(parts[1])
                month = int(parts[2])
                break

        if year is None or month is None:
            return

        year_stat = self._year_stats[year]
        month_stat = year_stat.months[month]
        month_stat.selected = not month_stat.selected

        # Update checkbox
        checkbox = "☑" if month_stat.selected else "☐"
        self.tree.item(item, text=f"{checkbox} {month_stat.month_name}")

        # Update year checkbox (partial selection)
        year_item = self._tree_items.get(f"year_{year}")
        if year_item:
            all_selected = all(m.selected for m in year_stat.months.values())
            year_stat.selected = all_selected
            checkbox = "☑" if all_selected else "☐"
            self.tree.item(year_item, text=f"{checkbox} {year}")

        self._update_summary()

        if self.on_selection_changed:
            self.on_selection_changed()

    def _update_summary(self):
        """Update summary label with selection statistics"""
        total_selected = 0
        total_size = 0

        for year_stat in self._year_stats.values():
            for month_stat in year_stat.months.values():
                if month_stat.selected:
                    total_selected += month_stat.photo_count
                    total_size += month_stat.total_size

        if total_selected > 0:
            self.summary_label.configure(
                text=f"Selected: {total_selected} photos ({format_size(total_size)})",
                text_color="green"
            )
        else:
            self.summary_label.configure(
                text="No photos selected",
                text_color="gray"
            )

    def get_selected_count(self) -> int:
        """Get count of selected photos"""
        total = 0
        for year_stat in self._year_stats.values():
            for month_stat in year_stat.months.values():
                if month_stat.selected:
                    total += month_stat.photo_count
        return total

    def set_enabled(self, enabled: bool):
        """Enable or disable the tree view"""
        state = "normal" if enabled else "disabled"
        self.tree.configure(selectmode="none" if enabled else "none")

    def show_loading(self):
        """Show loading animation"""
        self.tree_frame.pack_forget()
        self.loading_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self._animation_running = True
        self._animate_spinner()

    def hide_loading(self):
        """Hide loading animation"""
        self._animation_running = False
        self.loading_frame.pack_forget()
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def _animate_spinner(self):
        """Animate the loading spinner"""
        if not self._animation_running:
            return

        # Braille spinner characters for smooth animation
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_index = (self._spinner_index + 1) % len(spinner_chars)

        self.loading_label.configure(
            text=f"{spinner_chars[self._spinner_index]} Analyzing media..."
        )

        # Schedule next animation frame
        self.after(100, self._animate_spinner)
