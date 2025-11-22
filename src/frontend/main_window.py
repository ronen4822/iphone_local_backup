"""Main application window"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import logging
from typing import Optional, Dict

from ..backend.device_manager import DeviceManager
from ..backend.photo_analyzer import PhotoAnalyzer
from ..backend.photo_transfer import PhotoTransferManager
from ..backend.models import YearStats, TransferProgress
from ..core.config import AppConfig
from ..core.utils import setup_logging, validate_export_path
from ..core.settings_manager import SettingsManager, FolderOrganization
from .components.device_selector import DeviceSelector
from .components.photo_tree import PhotoTreeView
from .components.progress_panel import ProgressPanel
from .components.stats_panel import StatsPanel

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Setup logging
        setup_logging()

        # Window configuration
        self.title(AppConfig.APP_NAME)
        self.geometry(f"{AppConfig.WINDOW_WIDTH}x{AppConfig.WINDOW_HEIGHT}")
        self.minsize(AppConfig.MIN_WIDTH, AppConfig.MIN_HEIGHT)

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme(AppConfig.COLOR_THEME)

        # Initialize settings manager
        self.settings_manager = SettingsManager()

        # Initialize backend
        self.device_manager = DeviceManager()
        self.photo_analyzer = PhotoAnalyzer(self.device_manager)
        self.transfer_manager = PhotoTransferManager(self.device_manager)

        # State
        self._year_stats: Dict[int, YearStats] = {}
        self._export_path: Optional[Path] = None
        self._is_analyzing = False

        # Setup UI
        self._setup_ui()

        # Initial device scan
        self._refresh_devices()

        # Start progress monitor
        self._start_progress_monitor()

    def _setup_ui(self):
        """Setup the user interface"""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text=AppConfig.APP_NAME,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="left")

        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Left panel (device and export settings)
        left_panel = ctk.CTkFrame(content_frame, width=350)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.grid_propagate(False)

        # Device selector with analyze button
        self.device_selector = DeviceSelector(
            left_panel,
            on_device_selected=self._on_device_selected,
            on_analyze_clicked=self._start_analysis,
            on_refresh_clicked=self._refresh_devices
        )
        self.device_selector.pack(fill="x", padx=10, pady=10)

        # Export path section
        export_frame = ctk.CTkFrame(left_panel)
        export_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            export_frame,
            text="Export Folder",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5), padx=10, anchor="w")

        path_frame = ctk.CTkFrame(export_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=10, pady=5)

        self.path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="Select export folder..."
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        # Load saved path or use default
        saved_path = self.settings_manager.get_export_path()
        self.path_entry.insert(0, saved_path if saved_path else AppConfig.DEFAULT_EXPORT_FOLDER)

        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self._browse_export_path,
            width=80
        )
        browse_btn.pack(side="right")

        # Folder organization section
        org_label = ctk.CTkLabel(
            export_frame,
            text="Folder Organization",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        org_label.pack(pady=(10, 5), padx=10, anchor="w")

        self.folder_org_var = ctk.StringVar(value=self.settings_manager.get_folder_organization().value)

        # Use segmented button for clearer UX
        self.folder_org_segment = ctk.CTkSegmentedButton(
            export_frame,
            values=["Year/Month", "Year Only"],
            command=self._on_folder_org_segment_changed
        )
        self.folder_org_segment.pack(fill="x", padx=10, pady=5)

        # Set initial value
        if self.settings_manager.get_folder_organization() == FolderOrganization.YEAR_MONTH:
            self.folder_org_segment.set("Year/Month")
        else:
            self.folder_org_segment.set("Year Only")

        # Delete checkbox
        self.delete_var = ctk.BooleanVar(value=self.settings_manager.get_delete_after_export())
        delete_check = ctk.CTkCheckBox(
            export_frame,
            text="Delete media from device after export",
            variable=self.delete_var,
            command=self._on_delete_option_changed
        )
        delete_check.pack(pady=10, padx=10, anchor="w")

        # Progress panel
        self.progress_panel = ProgressPanel(left_panel)
        self.progress_panel.pack(fill="x", padx=10, pady=10)

        # Statistics panel
        self.stats_panel = StatsPanel(left_panel)
        self.stats_panel.pack(fill="x", padx=10, pady=10)
        self.stats_panel.update_stats(self.settings_manager.stats)

        # Right panel (photo tree)
        right_panel = ctk.CTkFrame(content_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")

        self.photo_tree = PhotoTreeView(
            right_panel,
            on_selection_changed=self._on_selection_changed
        )
        self.photo_tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Action buttons frame
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))

        self.export_btn = ctk.CTkButton(
            action_frame,
            text="Export Selected Media",
            command=self._start_export,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            state="disabled"
        )
        self.export_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            action_frame,
            text="Cancel",
            command=self._cancel_operation,
            font=ctk.CTkFont(size=14),
            height=45,
            fg_color="gray",
            hover_color="darkgray",
            state="disabled"
        )
        self.cancel_btn.pack(side="right", fill="x", expand=True)

    def _refresh_devices(self):
        """Refresh list of connected devices in background thread"""
        thread = threading.Thread(target=self._refresh_devices_worker, daemon=True)
        thread.start()

    def _refresh_devices_worker(self):
        """Worker thread for device refresh"""
        try:
            devices = self.device_manager.list_connected_devices()

            # Update UI on main thread
            self.after(0, lambda: self._on_devices_refreshed(devices))
        except Exception as e:
            logger.error(f"Device refresh failed: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to refresh devices: {e}"))

    def _on_devices_refreshed(self, devices):
        """Handle device refresh completion (runs on main thread)"""
        self.device_selector.update_devices(devices)

        if devices:
            # Auto-select first device
            self._on_device_selected(devices[0].udid)

    def _on_device_selected(self, udid: str):
        """Handle device selection in background thread"""
        thread = threading.Thread(target=self._connect_device_worker, args=(udid,), daemon=True)
        thread.start()

    def _connect_device_worker(self, udid: str):
        """Worker thread for device connection"""
        try:
            success = self.device_manager.connect_device(udid)

            # Update UI on main thread
            if success:
                logger.info(f"Connected to device: {udid}")
                self.after(0, lambda: self.device_selector.status_label.configure(
                    text="Device connected",
                    text_color="green"
                ))
            else:
                self.after(0, lambda: messagebox.showerror("Connection Error", "Failed to connect to device"))
                self.after(0, lambda: self.device_selector.status_label.configure(
                    text="Connection failed",
                    text_color="red"
                ))
        except Exception as e:
            logger.error(f"Device connection failed: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to connect: {e}"))

    def _browse_export_path(self):
        """Browse for export folder"""
        folder = filedialog.askdirectory(
            title="Select Export Folder",
            initialdir=self.path_entry.get() or str(Path.home())
        )
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            # Save the selected path
            self.settings_manager.set_export_path(folder)

    def _on_folder_org_segment_changed(self, value: str):
        """Handle folder organization change from segmented button"""
        if value == "Year/Month":
            org = FolderOrganization.YEAR_MONTH
        else:
            org = FolderOrganization.YEAR_ONLY

        self.folder_org_var.set(org.value)
        self.settings_manager.set_folder_organization(org)
        logger.info(f"Folder organization changed to: {org.value}")

    def _on_delete_option_changed(self):
        """Handle delete after export option change"""
        delete = self.delete_var.get()
        self.settings_manager.set_delete_after_export(delete)
        logger.info(f"Delete after export: {delete}")

    def _start_analysis(self):
        """Start photo analysis in background thread"""
        if self._is_analyzing:
            return

        # Validate device connection
        if not self.device_manager.is_connected():
            messagebox.showerror("Error", "No device connected")
            return

        self._is_analyzing = True
        self._set_ui_state(analyzing=True)
        self.progress_panel.reset()
        self.photo_tree.show_loading()

        # Start analysis thread
        thread = threading.Thread(target=self._analyze_photos, daemon=True)
        thread.start()

    def _analyze_photos(self):
        """Analyze photos (runs in background thread)"""
        try:
            def progress_callback(status: str, current: int, total: int):
                self.after(0, lambda: self.progress_panel.update_analysis_progress(status, current, total))

            self._year_stats = self.photo_analyzer.analyze_photos(progress_callback)

            # Update UI on main thread
            self.after(0, self._on_analysis_complete)

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.after(0, lambda: self._on_analysis_error(str(e)))

    def _on_analysis_complete(self):
        """Handle analysis completion"""
        self._is_analyzing = False
        self._set_ui_state(analyzing=False)

        self.photo_tree.hide_loading()
        self.photo_tree.load_photos(self._year_stats)
        self.progress_panel.reset()

        total_photos = sum(ys.photo_count for ys in self._year_stats.values())
        messagebox.showinfo(
            "Analysis Complete",
            f"Found {total_photos} media files (photos & videos) across {len(self._year_stats)} years"
        )

    def _on_analysis_error(self, error_msg: str):
        """Handle analysis error"""
        self._is_analyzing = False
        self._set_ui_state(analyzing=False)
        self.photo_tree.hide_loading()
        self.progress_panel.set_error(error_msg)
        messagebox.showerror("Analysis Error", f"Failed to analyze media:\n{error_msg}")

    def _on_selection_changed(self):
        """Handle photo selection change"""
        selected_count = self.photo_tree.get_selected_count()
        self.export_btn.configure(state="normal" if selected_count > 0 else "disabled")

    def _start_export(self):
        """Start photo export"""
        # Validate export path
        export_path_str = self.path_entry.get().strip()
        if not export_path_str:
            messagebox.showerror("Error", "Please select an export folder")
            return

        is_valid, error_msg = validate_export_path(export_path_str)
        if not is_valid:
            messagebox.showerror("Invalid Path", error_msg)
            return

        self._export_path = Path(export_path_str)

        # Get selected photos
        selected_photos = self.photo_analyzer.get_selected_photos(self._year_stats)
        if not selected_photos:
            messagebox.showwarning("No Selection", "Please select media files to export")
            return

        # Confirm export
        delete_text = " and delete from device" if self.delete_var.get() else ""
        confirm = messagebox.askyesno(
            "Confirm Export",
            f"Export {len(selected_photos)} media files to:\n{self._export_path}\n{delete_text}?"
        )

        if not confirm:
            return

        # Start transfer
        self._set_ui_state(transferring=True)

        # Get settings
        folder_org = self.settings_manager.get_folder_organization()
        batch_size = self.settings_manager.get_batch_size()

        self.transfer_manager.start_transfer(
            photos=selected_photos,
            export_path=self._export_path,
            delete_after_transfer=self.delete_var.get(),
            progress_callback=self._on_transfer_progress,
            folder_organization=folder_org,
            batch_size=batch_size
        )

    def _on_transfer_progress(self, progress: TransferProgress):
        """Handle transfer progress update"""
        self.after(0, lambda: self.progress_panel.update_progress(progress))

        # Handle completion
        if progress.status.value in ["completed", "failed", "cancelled"]:
            self.after(0, lambda: self._on_transfer_complete(progress))

    def _on_transfer_complete(self, progress: TransferProgress):
        """Handle transfer completion"""
        self._set_ui_state(transferring=False)

        if progress.status.value == "completed":
            # Update statistics
            if progress.completed_files > 0:
                self.settings_manager.update_export_stats(
                    files_exported=progress.completed_files,
                    size_exported=progress.transferred_size
                )
                self.stats_panel.update_stats(self.settings_manager.stats)

            messagebox.showinfo(
                "Export Complete",
                f"Successfully exported {progress.completed_files} media files\n"
                f"Failed: {progress.failed_files}"
            )
            # Refresh analysis after successful export
            if self.delete_var.get():
                self._start_analysis()
        elif progress.status.value == "failed":
            messagebox.showerror(
                "Export Failed",
                f"Transfer failed: {progress.error_message}"
            )
        elif progress.status.value == "cancelled":
            messagebox.showinfo("Cancelled", "Transfer was cancelled")

    def _cancel_operation(self):
        """Cancel ongoing operation"""
        if self.transfer_manager.is_transfer_active():
            confirm = messagebox.askyesno(
                "Cancel Transfer",
                "Are you sure you want to cancel the transfer?"
            )
            if confirm:
                self.transfer_manager.cancel_transfer()

    def _set_ui_state(self, analyzing: bool = False, transferring: bool = False):
        """Set UI state based on operation"""
        is_busy = analyzing or transferring

        self.device_selector.set_enabled(not is_busy)
        self.device_selector.set_analyze_enabled(not is_busy)
        self.export_btn.configure(state="disabled" if is_busy else "normal")
        self.cancel_btn.configure(state="normal" if transferring else "disabled")
        self.photo_tree.set_enabled(not is_busy)

    def _start_progress_monitor(self):
        """Monitor transfer progress"""
        if self.transfer_manager.is_transfer_active():
            progress = self.transfer_manager.get_current_progress()
            if progress:
                self.progress_panel.update_progress(progress)

        # Schedule next check
        self.after(500, self._start_progress_monitor)

    def on_closing(self):
        """Handle window closing"""
        if self.transfer_manager.is_transfer_active():
            confirm = messagebox.askyesno(
                "Transfer in Progress",
                "A transfer is in progress. Are you sure you want to quit?"
            )
            if not confirm:
                return

        self.device_manager.disconnect_device()
        self.destroy()


def run_app():
    """Run the application"""
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
