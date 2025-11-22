"""Statistics display panel component"""
import customtkinter as ctk
from typing import Optional
from datetime import datetime
from ...core.settings_manager import ExportStats


class StatsPanel(ctk.CTkFrame):
    """Panel for displaying export statistics"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Title
        title = ctk.CTkLabel(
            self,
            text="Export Statistics",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(10, 5), padx=10, anchor="w")

        # Stats container
        stats_container = ctk.CTkFrame(self, fg_color="transparent")
        stats_container.pack(fill="x", padx=10, pady=5)

        # Total files
        self.files_label = ctk.CTkLabel(
            stats_container,
            text="Total Exported: 0 files",
            font=ctk.CTkFont(size=12)
        )
        self.files_label.pack(anchor="w", pady=2)

        # Total size
        self.size_label = ctk.CTkLabel(
            stats_container,
            text="Total Size: 0 GB",
            font=ctk.CTkFont(size=12)
        )
        self.size_label.pack(anchor="w", pady=2)

        # Total exports
        self.exports_label = ctk.CTkLabel(
            stats_container,
            text="Export Sessions: 0",
            font=ctk.CTkFont(size=12)
        )
        self.exports_label.pack(anchor="w", pady=2)

        # Last export
        self.last_export_label = ctk.CTkLabel(
            stats_container,
            text="Last Export: Never",
            font=ctk.CTkFont(size=12)
        )
        self.last_export_label.pack(anchor="w", pady=2)

    def update_stats(self, stats: ExportStats):
        """Update the displayed statistics"""
        self.files_label.configure(
            text=f"Total Exported: {stats.total_files_exported:,} files"
        )

        if stats.size_gb >= 1:
            size_text = f"{stats.size_gb:.2f} GB"
        else:
            size_text = f"{stats.size_mb:.2f} MB"

        self.size_label.configure(text=f"Total Size: {size_text}")
        self.exports_label.configure(text=f"Export Sessions: {stats.total_exports}")

        if stats.last_export_date:
            try:
                last_date = datetime.fromisoformat(stats.last_export_date)
                date_str = last_date.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = "Unknown"
        else:
            date_str = "Never"

        self.last_export_label.configure(text=f"Last Export: {date_str}")
