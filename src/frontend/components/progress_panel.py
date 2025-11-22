"""Progress display panel for operations"""
import customtkinter as ctk
from typing import Optional

from ...backend.models import TransferProgress, TransferStatus
from ...core.utils import format_size


class ProgressPanel(ctk.CTkFrame):
    """Panel for displaying operation progress"""

    def __init__(self, parent):
        super().__init__(parent)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components"""
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Progress",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=(10, 5), padx=10, anchor="w")

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(pady=5, padx=10, anchor="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(pady=10, padx=10, fill="x")
        self.progress_bar.set(0)

        # Details frame
        details_frame = ctk.CTkFrame(self, fg_color="transparent")
        details_frame.pack(fill="x", padx=10, pady=5)

        # Files progress
        files_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        files_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            files_frame,
            text="Files:",
            font=ctk.CTkFont(size=11),
            width=60,
            anchor="w"
        ).pack(side="left")

        self.files_label = ctk.CTkLabel(
            files_frame,
            text="0 / 0",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.files_label.pack(side="left")

        # Size progress
        size_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        size_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            size_frame,
            text="Size:",
            font=ctk.CTkFont(size=11),
            width=60,
            anchor="w"
        ).pack(side="left")

        self.size_label = ctk.CTkLabel(
            size_frame,
            text="0 B / 0 B",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.size_label.pack(side="left")

        # Current file
        current_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        current_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            current_frame,
            text="Current:",
            font=ctk.CTkFont(size=11),
            width=60,
            anchor="w"
        ).pack(side="left")

        self.current_file_label = ctk.CTkLabel(
            current_frame,
            text="-",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.current_file_label.pack(side="left", fill="x", expand=True)

    def update_progress(self, progress: TransferProgress):
        """Update progress display"""
        # Update progress bar
        progress_value = progress.progress_percent / 100.0
        self.progress_bar.set(progress_value)

        # Update status
        status_text = self._get_status_text(progress.status)
        status_color = self._get_status_color(progress.status)
        self.status_label.configure(text=status_text, text_color=status_color)

        # Update files
        self.files_label.configure(
            text=f"{progress.completed_files} / {progress.total_files}"
        )

        # Update size
        self.size_label.configure(
            text=f"{format_size(progress.transferred_size)} / {format_size(progress.total_size)}"
        )

        # Update current file
        if progress.current_file:
            # Truncate long filenames
            filename = progress.current_file
            if len(filename) > 40:
                filename = filename[:37] + "..."
            self.current_file_label.configure(text=filename)
        else:
            self.current_file_label.configure(text="-")

        # Show failed files if any
        if progress.failed_files > 0:
            self.status_label.configure(
                text=f"{status_text} ({progress.failed_files} failed)",
                text_color="orange"
            )

    def update_analysis_progress(self, status: str, current: int, total: int):
        """Update progress for analysis operation"""
        self.status_label.configure(text=status, text_color="blue")

        if total > 0:
            progress_value = current / total
            self.progress_bar.set(progress_value)
            self.files_label.configure(text=f"{current} / {total}")
        else:
            # Indeterminate progress
            self.progress_bar.set(0.5)
            self.files_label.configure(text=f"{current}")

        self.current_file_label.configure(text="-")
        self.size_label.configure(text="-")

    def reset(self):
        """Reset progress display"""
        self.status_label.configure(text="Ready", text_color="gray")
        self.progress_bar.set(0)
        self.files_label.configure(text="0 / 0")
        self.size_label.configure(text="0 B / 0 B")
        self.current_file_label.configure(text="-")

    def set_error(self, message: str):
        """Display error message"""
        self.status_label.configure(text=f"Error: {message}", text_color="red")
        self.progress_bar.set(0)

    def _get_status_text(self, status: TransferStatus) -> str:
        """Get display text for transfer status"""
        status_map = {
            TransferStatus.PENDING: "Pending",
            TransferStatus.IN_PROGRESS: "Transferring photos...",
            TransferStatus.COMPLETED: "Transfer completed",
            TransferStatus.FAILED: "Transfer failed",
            TransferStatus.CANCELLED: "Transfer cancelled"
        }
        return status_map.get(status, "Unknown")

    def _get_status_color(self, status: TransferStatus) -> str:
        """Get color for transfer status"""
        color_map = {
            TransferStatus.PENDING: "gray",
            TransferStatus.IN_PROGRESS: "blue",
            TransferStatus.COMPLETED: "green",
            TransferStatus.FAILED: "red",
            TransferStatus.CANCELLED: "orange"
        }
        return color_map.get(status, "gray")
