"""Application configuration and constants"""
from pathlib import Path
from typing import List


class AppConfig:
    """Application configuration settings"""

    # Application metadata
    APP_NAME = "iPhone Media Backup"
    APP_VERSION = "0.1.0"

    # Window settings
    WINDOW_WIDTH = 1100
    WINDOW_HEIGHT = 1200
    MIN_WIDTH = 1000
    MIN_HEIGHT = 750

    # Theme settings
    THEME = "dark-blue"
    COLOR_THEME = "blue"

    # Photo file extensions
    PHOTO_EXTENSIONS: List[str] = [
        '.jpg', '.jpeg', '.png', '.heic', '.heif',
        '.gif', '.tiff', '.bmp', '.raw', '.cr2', '.nef', '.dng'
    ]

    # Video file extensions
    VIDEO_EXTENSIONS: List[str] = [
        '.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.wmv', '.flv'
    ]

    # Transfer settings
    BATCH_SIZE = 10  # Number of files to transfer before checking device connection
    BUFFER_SIZE = 8192  # Buffer size for file operations

    # Progress update frequency
    PROGRESS_UPDATE_INTERVAL = 0.5  # seconds

    # Default export folder
    DEFAULT_EXPORT_FOLDER = str(Path.home() / "iPhone_Photos")

    # Device connection settings
    CONNECTION_TIMEOUT = 10  # seconds
    RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAY = 2  # seconds
