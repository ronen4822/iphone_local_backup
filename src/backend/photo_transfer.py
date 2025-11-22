"""Media transfer operations (photos and videos) with device disconnection handling"""
import logging
import threading
from pathlib import Path
from typing import List, Callable, Optional
import time

from pymobiledevice3.services.afc import AfcService

from ..backend.models import Photo, TransferProgress, TransferStatus
from ..backend.device_manager import DeviceManager
from ..core.config import AppConfig
from ..core.settings_manager import FolderOrganization
from ..core.utils import create_export_path, sanitize_filename

logger = logging.getLogger(__name__)


class PhotoTransferManager:
    """Manages media transfer operations (photos and videos) with device disconnection handling"""

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self._is_cancelled = False
        self._transfer_thread: Optional[threading.Thread] = None
        self._current_progress: Optional[TransferProgress] = None

    def start_transfer(self,
                       photos: List[Photo],
                       export_path: Path,
                       delete_after_transfer: bool = True,
                       progress_callback: Optional[Callable[[TransferProgress], None]] = None,
                       folder_organization: FolderOrganization = FolderOrganization.YEAR_MONTH,
                       batch_size: int = None
                       ) -> None:
        """
        Start photo transfer in background thread

        Args:
            photos: List of photos to transfer
            export_path: Base export directory
            delete_after_transfer: Whether to delete photos from device after transfer
            progress_callback: Optional callback for progress updates
            folder_organization: How to organize folders (year/month or year only)
            batch_size: Number of files to transfer before checking connection (None = use default)
        """
        if self._transfer_thread and self._transfer_thread.is_alive():
            raise RuntimeError("Transfer already in progress")

        self._is_cancelled = False
        self._transfer_thread = threading.Thread(
            target=self._transfer_worker,
            args=(photos, export_path, delete_after_transfer, progress_callback, folder_organization, batch_size),
            daemon=True
        )
        self._transfer_thread.start()

    def cancel_transfer(self) -> None:
        """Cancel ongoing transfer"""
        self._is_cancelled = True
        logger.info("Transfer cancellation requested")

    def is_transfer_active(self) -> bool:
        """Check if transfer is currently active"""
        return self._transfer_thread is not None and self._transfer_thread.is_alive()

    def get_current_progress(self) -> Optional[TransferProgress]:
        """Get current transfer progress"""
        return self._current_progress

    def _transfer_worker(self,
                         photos: List[Photo],
                         export_path: Path,
                         delete_after_transfer: bool,
                         progress_callback: Optional[Callable[[TransferProgress], None]],
                         folder_organization: FolderOrganization,
                         batch_size: Optional[int]
                         ) -> None:
        """Worker thread for photo transfer"""
        total_size = sum(p.size for p in photos)

        self._current_progress = TransferProgress(
            total_files=len(photos),
            completed_files=0,
            failed_files=0,
            total_size=total_size,
            transferred_size=0,
            status=TransferStatus.IN_PROGRESS
        )

        try:
            self._transfer_photos(
                photos,
                export_path,
                delete_after_transfer,
                progress_callback,
                folder_organization,
                batch_size
            )

            if self._is_cancelled:
                self._current_progress.status = TransferStatus.CANCELLED
                logger.info("Transfer cancelled")
            else:
                self._current_progress.status = TransferStatus.COMPLETED
                logger.info("Transfer completed successfully")

        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            self._current_progress.status = TransferStatus.FAILED
            self._current_progress.error_message = str(e)

        finally:
            if progress_callback:
                progress_callback(self._current_progress)

    def _transfer_photos(self,
                         photos: List[Photo],
                         export_path: Path,
                         delete_after_transfer: bool,
                         progress_callback: Optional[Callable[[TransferProgress], None]],
                         folder_organization: FolderOrganization,
                         batch_size: Optional[int]
                         ) -> None:
        """Transfer photos with batch processing and reconnection handling"""
        batch_count = 0
        failed_photos = []
        # Use provided batch size or fall back to default
        effective_batch_size = batch_size if batch_size is not None else AppConfig.BATCH_SIZE

        with self.device_manager.get_afc_service() as afc:
            for idx, photo in enumerate(photos):
                if self._is_cancelled:
                    break

                # Check connection periodically
                if batch_count >= effective_batch_size:
                    if not self._verify_and_reconnect():
                        raise RuntimeError("Device disconnected and could not reconnect")
                    batch_count = 0

                # Update current file
                self._current_progress.current_file = photo.filename

                try:
                    # Transfer photo
                    success = self._transfer_single_photo(afc, photo, export_path, folder_organization)

                    if success:
                        self._current_progress.completed_files += 1
                        self._current_progress.transferred_size += photo.size

                        # Delete from device if requested
                        if delete_after_transfer:
                            self._delete_photo(afc, photo)
                    else:
                        self._current_progress.failed_files += 1
                        failed_photos.append(photo)

                except Exception as e:
                    logger.error(f"Error transferring {photo.filename}: {e}")
                    self._current_progress.failed_files += 1
                    failed_photos.append(photo)

                batch_count += 1

                # Send progress update
                if progress_callback:
                    progress_callback(self._current_progress)

        # Log failed photos
        if failed_photos:
            logger.warning(f"{len(failed_photos)} photos failed to transfer")
            for photo in failed_photos:
                logger.warning(f"Failed: {photo.filename}")

    def _transfer_single_photo(self,
                               afc: AfcService,
                               photo: Photo,
                               base_export_path: Path,
                               folder_organization: FolderOrganization = FolderOrganization.YEAR_MONTH
                               ) -> bool:
        """Transfer a single photo from device to local storage"""
        try:
            # Create directory structure based on organization preference
            year_only = (folder_organization == FolderOrganization.YEAR_ONLY)
            export_dir = create_export_path(base_export_path, photo.year, photo.month, year_only=year_only)

            # Sanitize filename
            safe_filename = sanitize_filename(photo.filename)
            target_path = export_dir / safe_filename

            # Use pull method to download file from device (will override if file exists)
            afc.pull(
                relative_src=photo.path,
                dst=str(target_path),
                progress_bar=False
            )

            logger.debug(f"Transferred: {photo.filename} -> {target_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to transfer {photo.filename}: {e}")
            return False

    def _delete_photo(self, afc: AfcService, photo: Photo) -> bool:
        """Delete photo from device"""
        try:
            afc.rm(photo.path)
            logger.debug(f"Deleted from device: {photo.filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {photo.filename}: {e}")
            return False

    def _verify_and_reconnect(self) -> bool:
        """Verify device connection and attempt reconnection if needed"""
        is_connected, error_msg = self.device_manager.verify_connection()

        if is_connected:
            return True

        logger.warning(f"Device connection issue: {error_msg}")

        # Attempt to reconnect
        for attempt in range(AppConfig.RECONNECT_ATTEMPTS):
            logger.info(f"Reconnection attempt {attempt + 1}/{AppConfig.RECONNECT_ATTEMPTS}")
            time.sleep(AppConfig.RECONNECT_DELAY)

            if self.device_manager.is_connected():
                logger.info("Reconnection successful")
                return True

        logger.error("Failed to reconnect to device")
        return False
