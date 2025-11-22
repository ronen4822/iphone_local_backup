"""Device selection component"""
import customtkinter as ctk
from typing import List, Callable, Optional

from ...backend.models import DeviceInfo


class DeviceSelector(ctk.CTkFrame):
    """Component for selecting iOS devices"""

    def __init__(self, parent, on_device_selected: Optional[Callable[[str], None]] = None,
                 on_analyze_clicked: Optional[Callable[[], None]] = None,
                 on_refresh_clicked: Optional[Callable[[], None]] = None):
        super().__init__(parent)

        self.on_device_selected = on_device_selected
        self.on_analyze_clicked = on_analyze_clicked
        self.on_refresh_clicked = on_refresh_clicked
        self._current_devices: List[DeviceInfo] = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="Select Device",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(pady=(10, 5), padx=10, anchor="w")

        # Device dropdown
        self.device_combo = ctk.CTkComboBox(
            self,
            values=["No devices found"],
            state="readonly",
            command=self._on_device_changed,
            width=300
        )
        self.device_combo.pack(pady=5, padx=10, fill="x")

        # Buttons frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=5, padx=10, fill="x")

        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            button_frame,
            text="Refresh",
            command=self._on_refresh_clicked,
            width=100,
            height=35
        )
        self.refresh_btn.pack(side="left", padx=(0, 5))

        # Analyze button (initially disabled until device is connected)
        self.analyze_btn = ctk.CTkButton(
            button_frame,
            text="Analyze Media",
            command=self._on_analyze_clicked,
            width=190,
            height=35,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=["#3B8ED0", "#1F6AA5"],
            hover_color=["#36719F", "#144870"],
            state="disabled"
        )
        self.analyze_btn.pack(side="left", fill="x", expand=True)

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_label.pack(pady=(5, 10), padx=10)

    def update_devices(self, devices: List[DeviceInfo]):
        """Update the list of available devices"""
        self._current_devices = devices

        if devices:
            device_names = [str(device) for device in devices]
            self.device_combo.configure(values=device_names)
            self.device_combo.set(device_names[0])
            self.status_label.configure(
                text=f"{len(devices)} device(s) found",
                text_color="green"
            )
            # Enable analyze button when devices are found
            self.analyze_btn.configure(state="normal")
        else:
            self.device_combo.configure(values=["No devices found"])
            self.device_combo.set("No devices found")
            self.status_label.configure(
                text="No devices connected",
                text_color="orange"
            )
            # Disable analyze button when no devices
            self.analyze_btn.configure(state="disabled")

    def get_selected_device(self) -> Optional[DeviceInfo]:
        """Get currently selected device"""
        if not self._current_devices:
            return None

        current_index = self.device_combo.cget("values").index(self.device_combo.get())
        if 0 <= current_index < len(self._current_devices):
            return self._current_devices[current_index]

        return None

    def _on_device_changed(self, choice):
        """Handle device selection change"""
        device = self.get_selected_device()
        if device and self.on_device_selected:
            self.on_device_selected(device.udid)

    def _on_refresh_clicked(self):
        """Handle refresh button click"""
        self.status_label.configure(text="Refreshing...", text_color="blue")
        # Trigger refresh callback
        if self.on_refresh_clicked:
            self.on_refresh_clicked()

    def _on_analyze_clicked(self):
        """Handle analyze button click"""
        if self.on_analyze_clicked:
            self.on_analyze_clicked()

    def set_enabled(self, enabled: bool):
        """Enable or disable the component"""
        state = "normal" if enabled else "disabled"
        self.device_combo.configure(state="readonly" if enabled else "disabled")
        self.refresh_btn.configure(state=state)

    def set_analyze_enabled(self, enabled: bool):
        """Enable or disable the analyze button"""
        # Only enable if we have devices and the enabled flag is True
        if enabled and self._current_devices:
            self.analyze_btn.configure(state="normal")
        else:
            self.analyze_btn.configure(state="disabled")
