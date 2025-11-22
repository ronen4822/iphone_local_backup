"""Utility functions for the application"""
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('iphone_backup.log')
        ]
    )


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def create_export_path(base_path: Path, year: int, month: int, year_only: bool = False) -> Path:
    """
    Create export path structure for year and optionally month

    Args:
        base_path: Base export directory
        year: Year for organization
        month: Month for organization (1-12)
        year_only: If True, only organize by year; if False, organize by year and month

    Returns:
        Path to the export directory
    """
    if year_only:
        export_path = base_path / str(year)
    else:
        month_names = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        export_path = base_path / str(year) / f"{month:02d}_{month_names[month - 1]}"

    export_path.mkdir(parents=True, exist_ok=True)
    return export_path


def get_unique_filepath(filepath: Path) -> Path:
    """Get unique filepath by appending number if file exists"""
    if not filepath.exists():
        return filepath

    counter = 1
    stem = filepath.stem
    suffix = filepath.suffix
    parent = filepath.parent

    while True:
        new_filepath = parent / f"{stem}_{counter}{suffix}"
        if not new_filepath.exists():
            return new_filepath
        counter += 1


def validate_export_path(path: str) -> tuple[bool, Optional[str]]:
    """Validate export path and return (is_valid, error_message)"""
    try:
        export_path = Path(path)

        if not export_path.exists():
            export_path.mkdir(parents=True, exist_ok=True)

        if not export_path.is_dir():
            return False, "Path is not a directory"

        # Test write permission
        test_file = export_path / ".test_write"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception:
            return False, "No write permission for this directory"

        return True, None
    except Exception as e:
        return False, f"Invalid path: {str(e)}"
