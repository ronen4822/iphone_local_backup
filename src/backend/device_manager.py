"""Device management for iOS devices"""
import logging
from typing import Optional, List
from contextlib import contextmanager

from pymobiledevice3.lockdown import LockdownClient, create_using_usbmux
from pymobiledevice3.services.afc import AfcService
from pymobiledevice3.usbmux import list_devices

from ..backend.models import DeviceInfo
from ..core.config import AppConfig

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages iOS device connections and operations"""

    def __init__(self):
        self._current_device: Optional[LockdownClient] = None
        self._device_info: Optional[DeviceInfo] = None

    def list_connected_devices(self) -> List[DeviceInfo]:
        """List all connected iOS devices"""
        devices = []
        try:
            device_list = list_devices()

            for device in device_list:
                try:
                    lockdown = create_using_usbmux(serial=device.serial)
                    device_info = DeviceInfo(
                        udid=lockdown.udid,
                        name=lockdown.all_values.get('DeviceName', 'Unknown Device'),
                        ios_version=lockdown.all_values.get('ProductVersion', 'Unknown'),
                        device_class=lockdown.all_values.get('DeviceClass', 'Unknown'),
                        is_connected=True
                    )
                    devices.append(device_info)
                except Exception as e:
                    logger.error(f"Error getting device info: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error listing devices: {e}")

        return devices

    def connect_device(self, udid: str) -> bool:
        """Connect to a specific device by UDID"""
        try:
            self._current_device = create_using_usbmux(serial=udid)

            self._device_info = DeviceInfo(
                udid=self._current_device.udid,
                name=self._current_device.all_values.get('DeviceName', 'Unknown Device'),
                ios_version=self._current_device.all_values.get('ProductVersion', 'Unknown'),
                device_class=self._current_device.all_values.get('DeviceClass', 'Unknown'),
                is_connected=True
            )

            logger.info(f"Connected to device: {self._device_info}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to device {udid}: {e}")
            self._current_device = None
            self._device_info = None
            return False

    def disconnect_device(self) -> None:
        """Disconnect from current device"""
        if self._current_device:
            self._current_device = None
            self._device_info = None
            logger.info("Disconnected from device")

    def is_connected(self) -> bool:
        """Check if device is currently connected"""
        if not self._current_device or not self._device_info:
            return False

        try:
            # Verify device is still connected by checking device list
            devices = list_devices()
            return any(d.serial == self._device_info.udid for d in devices)
        except Exception:
            return False

    def get_current_device_info(self) -> Optional[DeviceInfo]:
        """Get information about currently connected device"""
        if self.is_connected():
            return self._device_info
        return None

    @contextmanager
    def get_afc_service(self):
        """Get AFC (Apple File Conduit) service for file operations"""
        if not self._current_device:
            raise RuntimeError("No device connected")

        afc = None
        try:
            afc = AfcService(lockdown=self._current_device)
            yield afc
        except Exception as e:
            logger.error(f"AFC service error: {e}")
            raise
        finally:
            if afc:
                try:
                    afc.close()
                except Exception:
                    pass

    def verify_connection(self) -> tuple[bool, Optional[str]]:
        """Verify device connection and return status with message"""
        if not self._current_device:
            return False, "No device connected"

        if not self.is_connected():
            return False, "Device disconnected"

        return True, None
