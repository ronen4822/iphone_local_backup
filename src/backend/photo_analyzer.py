"""Photo analysis and organization"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable, Optional
from collections import defaultdict

from pymobiledevice3.services.afc import AfcService

from ..backend.models import Photo, MonthStats, YearStats
from ..backend.device_manager import DeviceManager
from ..core.config import AppConfig

logger = logging.getLogger(__name__)


class PhotoAnalyzer:
    """Analyzes photos and videos on iOS device and organizes by year/month"""

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self._photo_paths = [
            '/DCIM',  # Camera Roll
            '/Media/DCIM',  # Alternative path
        ]

    def analyze_photos(self,
                       progress_callback: Optional[Callable[[str, int, int], None]] = None
                       ) -> Dict[int, YearStats]:
        """
        Analyze all photos and videos on device and organize by year/month

        Args:
            progress_callback: Optional callback function(status, current, total)

        Returns:
            Dictionary mapping year to YearStats
        """
        year_stats: Dict[int, YearStats] = {}
        photos_by_year_month: Dict[int, Dict[int, List[Photo]]] = defaultdict(lambda: defaultdict(list))

        try:
            with self.device_manager.get_afc_service() as afc:
                all_photos = self._find_all_photos(afc, progress_callback)

                total_photos = len(all_photos)
                logger.info(f"Found {total_photos} media files to analyze")

                # Organize photos by year and month
                for idx, photo in enumerate(all_photos):
                    if progress_callback and idx % 10 == 0:
                        progress_callback(
                            f"Organizing photo {idx + 1} of {total_photos}",
                            idx + 1,
                            total_photos
                        )

                    year = photo.year
                    month = photo.month
                    photos_by_year_month[year][month].append(photo)

                # Create statistics for each year and month
                for year, months in photos_by_year_month.items():
                    year_stat = YearStats(year=year)

                    for month, photos in months.items():
                        month_stat = MonthStats(
                            year=year,
                            month=month,
                            photo_count=len(photos),
                            total_size=sum(p.size for p in photos),
                            photos=photos
                        )
                        year_stat.add_month(month_stat)

                    year_stats[year] = year_stat

                if progress_callback:
                    progress_callback("Analysis complete", total_photos, total_photos)

        except Exception as e:
            logger.error(f"Error analyzing photos: {e}")
            raise

        return year_stats

    def _find_all_photos(self,
                         afc: AfcService,
                         progress_callback: Optional[Callable[[str, int, int], None]] = None
                         ) -> List[Photo]:
        """Find all photos and videos on the device"""
        all_photos = []
        # Use a list to track count across recursive calls (mutable reference)
        photo_counter = [0]

        for base_path in self._photo_paths:
            try:
                if not self._path_exists(afc, base_path):
                    continue

                if progress_callback:
                    progress_callback(f"Scanning {base_path}...", photo_counter[0], photo_counter[0])

                photos = self._scan_directory_recursive(afc, base_path, progress_callback, photo_counter)
                all_photos.extend(photos)

            except Exception as e:
                logger.warning(f"Could not scan {base_path}: {e}")
                continue

        return all_photos

    def _scan_directory_recursive(self,
                                   afc: AfcService,
                                   path: str,
                                   progress_callback: Optional[Callable[[str, int, int], None]] = None,
                                   photo_counter: Optional[list] = None
                                   ) -> List[Photo]:
        """Recursively scan directory for photos"""
        photos = []
        if photo_counter is None:
            photo_counter = [0]

        try:
            items = afc.listdir(path)

            for item in items:
                if item in ('.', '..'):
                    continue

                item_path = f"{path}/{item}" if not path.endswith('/') else f"{path}{item}"

                try:
                    info = afc.stat(item_path)

                    # Check if it's a directory
                    if info.get('st_ifmt') == 'S_IFDIR':
                        # Recursively scan subdirectory
                        photos.extend(self._scan_directory_recursive(afc, item_path, progress_callback, photo_counter))
                    else:
                        # Check if it's a photo or video
                        if self._is_photo_file(item):
                            photo = self._create_photo_from_stat(item_path, info)
                            if photo:
                                photos.append(photo)
                                photo_counter[0] += 1

                                if progress_callback and photo_counter[0] % 50 == 0:
                                    progress_callback(
                                        f"Found {photo_counter[0]} media files...",
                                        photo_counter[0],
                                        photo_counter[0]
                                    )

                except Exception as e:
                    logger.debug(f"Error processing item {item_path}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error scanning directory {path}: {e}")

        return photos

    def _is_photo_file(self, filename: str) -> bool:
        """Check if file is a photo or video based on extension"""
        ext = Path(filename).suffix.lower()
        return ext in AppConfig.PHOTO_EXTENSIONS or ext in AppConfig.VIDEO_EXTENSIONS

    def _create_photo_from_stat(self, path: str, stat_info: dict) -> Optional[Photo]:
        """Create Photo object from file stat information"""
        try:
            # Get file size
            size = stat_info.get('st_size', 0)

            # Get creation time (birth time) - only use this for grouping
            created_date = stat_info.get('st_birthtime', None)
            if created_date is None:
                # Skip files without creation date - we only want to group by actual creation date
                logger.debug(f"Skipping {path}: no creation date available")
                return None

            # Get modification time (stored but not used for grouping)
            modified_date = stat_info.get('st_mtime', None)

            return Photo(
                filename=Path(path).name,
                path=path,
                size=size,
                created_date=created_date,
                modified_date=modified_date
            )

        except Exception as e:
            logger.error(f"Error creating Photo object for {path}: {e}")
            return None

    def _path_exists(self, afc: AfcService, path: str) -> bool:
        """Check if path exists on device"""
        try:
            afc.stat(path)
            return True
        except Exception:
            return False

    def get_selected_photos(self, year_stats: Dict[int, YearStats]) -> List[Photo]:
        """Get all photos from selected years and months"""
        selected_photos = []

        for year_stat in year_stats.values():
            if year_stat.selected:
                # All months in this year are selected
                for month_stat in year_stat.months.values():
                    selected_photos.extend(month_stat.photos)
            else:
                # Only selected months
                for month_stat in year_stat.months.values():
                    if month_stat.selected:
                        selected_photos.extend(month_stat.photos)

        return selected_photos
