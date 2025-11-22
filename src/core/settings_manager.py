"""Settings and statistics manager with persistent storage"""
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class FolderOrganization(Enum):
    """How to organize exported photos into folders"""
    YEAR_MONTH = "year_month"  # Separate folders for each year and month
    YEAR_ONLY = "year_only"    # Only year folders


@dataclass
class ExportStats:
    """Statistics about export operations"""
    total_files_exported: int = 0
    total_size_exported: int = 0  # in bytes
    last_export_date: Optional[str] = None
    total_exports: int = 0

    @property
    def size_mb(self) -> float:
        """Return total size in megabytes"""
        return self.total_size_exported / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Return total size in gigabytes"""
        return self.total_size_exported / (1024 * 1024 * 1024)


@dataclass
class UserSettings:
    """User preferences and settings"""
    export_path: str = ""
    folder_organization: str = FolderOrganization.YEAR_MONTH.value
    batch_size: int = 50
    delete_after_export: bool = True


class SettingsManager:
    """Manages application settings and statistics with persistent storage"""

    def __init__(self):
        self._settings_dir = self._get_settings_directory()
        self._settings_file = self._settings_dir / "settings.json"
        self._stats_file = self._settings_dir / "stats.json"

        # Ensure settings directory exists
        self._settings_dir.mkdir(parents=True, exist_ok=True)

        # Load settings and stats
        self.settings = self._load_settings()
        self.stats = self._load_stats()

    @staticmethod
    def _get_settings_directory() -> Path:
        """Get platform-specific settings directory"""
        import platform

        system = platform.system()

        if system == "Windows":
            # Use AppData\Local on Windows
            base = Path.home() / "AppData" / "Local"
        elif system == "Darwin":
            # Use Application Support on macOS
            base = Path.home() / "Library" / "Application Support"
        else:
            # Use .config on Linux/Unix
            base = Path.home() / ".config"

        return base / "iPhonePhotoBackup"

    def _load_settings(self) -> UserSettings:
        """Load settings from file"""
        if not self._settings_file.exists():
            logger.info("No settings file found, using defaults")
            return UserSettings()

        try:
            with open(self._settings_file, 'r') as f:
                data = json.load(f)
            logger.info("Settings loaded successfully")
            return UserSettings(**data)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return UserSettings()

    def _load_stats(self) -> ExportStats:
        """Load statistics from file"""
        if not self._stats_file.exists():
            logger.info("No stats file found, using defaults")
            return ExportStats()

        try:
            with open(self._stats_file, 'r') as f:
                data = json.load(f)
            logger.info("Stats loaded successfully")
            return ExportStats(**data)
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
            return ExportStats()

    def save_settings(self) -> bool:
        """Save current settings to file"""
        try:
            with open(self._settings_file, 'w') as f:
                json.dump(asdict(self.settings), f, indent=2)
            logger.info("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def save_stats(self) -> bool:
        """Save current statistics to file"""
        try:
            with open(self._stats_file, 'w') as f:
                json.dump(asdict(self.stats), f, indent=2)
            logger.info("Stats saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
            return False

    def update_export_stats(self, files_exported: int, size_exported: int) -> None:
        """Update statistics after an export operation"""
        self.stats.total_files_exported += files_exported
        self.stats.total_size_exported += size_exported
        self.stats.last_export_date = datetime.now().isoformat()
        self.stats.total_exports += 1
        self.save_stats()
        logger.info(f"Stats updated: +{files_exported} files, +{size_exported / (1024*1024):.2f} MB")

    def get_folder_organization(self) -> FolderOrganization:
        """Get folder organization preference as enum"""
        try:
            return FolderOrganization(self.settings.folder_organization)
        except ValueError:
            return FolderOrganization.YEAR_MONTH

    def set_folder_organization(self, org: FolderOrganization) -> None:
        """Set folder organization preference"""
        self.settings.folder_organization = org.value
        self.save_settings()

    def get_batch_size(self) -> int:
        """Get batch size preference"""
        return self.settings.batch_size

    def set_batch_size(self, size: int) -> None:
        """Set batch size preference"""
        self.settings.batch_size = size
        self.save_settings()

    def get_export_path(self) -> str:
        """Get saved export path"""
        return self.settings.export_path

    def set_export_path(self, path: str) -> None:
        """Set and save export path"""
        self.settings.export_path = path
        self.save_settings()

    def get_delete_after_export(self) -> bool:
        """Get delete after export preference"""
        return self.settings.delete_after_export

    def set_delete_after_export(self, delete: bool) -> None:
        """Set delete after export preference"""
        self.settings.delete_after_export = delete
        self.save_settings()
