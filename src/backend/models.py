"""Data models for photo management"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class TransferStatus(Enum):
    """Status of photo transfer operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Photo:
    """Represents a single photo on the device"""
    filename: str
    path: str
    size: int
    created_date: datetime
    modified_date: Optional[datetime] = None

    @property
    def size_mb(self) -> float:
        """Return size in megabytes"""
        return self.size / (1024 * 1024)

    @property
    def year(self) -> int:
        """Extract year from creation date"""
        if isinstance(self.created_date, datetime):
            return self.created_date.year
        # Fallback if created_date is somehow an int/float timestamp
        if isinstance(self.created_date, (int, float)):
            return datetime.fromtimestamp(self.created_date).year
        raise TypeError(f"created_date has invalid type: {type(self.created_date)}")

    @property
    def month(self) -> int:
        """Extract month from creation date"""
        if isinstance(self.created_date, datetime):
            return self.created_date.month
        # Fallback if created_date is somehow an int/float timestamp
        if isinstance(self.created_date, (int, float)):
            return datetime.fromtimestamp(self.created_date).month
        raise TypeError(f"created_date has invalid type: {type(self.created_date)}")


@dataclass
class MonthStats:
    """Statistics for photos in a specific month"""
    year: int
    month: int
    photo_count: int = 0
    total_size: int = 0
    photos: List[Photo] = field(default_factory=list)
    selected: bool = False

    @property
    def size_mb(self) -> float:
        """Return total size in megabytes"""
        return self.total_size / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Return total size in gigabytes"""
        return self.total_size / (1024 * 1024 * 1024)

    @property
    def month_name(self) -> str:
        """Return month name"""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return months[self.month - 1]


@dataclass
class YearStats:
    """Statistics for photos in a specific year"""
    year: int
    photo_count: int = 0
    total_size: int = 0
    months: dict[int, MonthStats] = field(default_factory=dict)
    selected: bool = False

    @property
    def size_mb(self) -> float:
        """Return total size in megabytes"""
        return self.total_size / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Return total size in gigabytes"""
        return self.total_size / (1024 * 1024 * 1024)

    def add_month(self, month_stats: MonthStats) -> None:
        """Add month statistics to this year"""
        self.months[month_stats.month] = month_stats
        self.photo_count += month_stats.photo_count
        self.total_size += month_stats.total_size


@dataclass
class DeviceInfo:
    """Information about connected iOS device"""
    udid: str
    name: str
    ios_version: str
    device_class: str
    is_connected: bool = True

    def __str__(self) -> str:
        return f"{self.name} (iOS {self.ios_version})"


@dataclass
class TransferProgress:
    """Progress information for transfer operations"""
    total_files: int
    completed_files: int
    failed_files: int
    total_size: int
    transferred_size: int
    current_file: Optional[str] = None
    status: TransferStatus = TransferStatus.PENDING
    error_message: Optional[str] = None

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.completed_files / self.total_files) * 100

    @property
    def size_progress_percent(self) -> float:
        """Calculate size-based progress percentage"""
        if self.total_size == 0:
            return 0.0
        return (self.transferred_size / self.total_size) * 100
