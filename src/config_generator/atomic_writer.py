"""Atomic file writer for safe configuration file updates."""

import os
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AtomicFileWriter:
    """
    Provides atomic file write operations using tempfile + os.replace pattern.

    This ensures that configuration files are never partially written or corrupted,
    which is critical for Asterisk configuration files.
    """

    @staticmethod
    def write_atomic(content: str, target_path: str) -> None:
        """
        Write content to target_path atomically.

        This method:
        1. Creates parent directories if they don't exist
        2. Writes content to a temporary file in the same directory as target
        3. Atomically replaces target with the temp file using os.replace()

        Args:
            content: String content to write
            target_path: Absolute path to target file

        Raises:
            ValueError: If target_path is not absolute
            IOError: If write or replace operation fails
            PermissionError: If insufficient permissions to write to target directory
        """
        # Validate target path
        if not os.path.isabs(target_path):
            raise ValueError(f"Target path must be absolute: {target_path}")

        target = Path(target_path)
        target_dir = target.parent

        logger.info(f"Starting atomic write to {target_path}")

        try:
            # Ensure parent directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {target_dir}")

            # Create temporary file in same directory as target
            # This ensures temp and target are on same filesystem (required for atomic replace)
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=target_dir,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
                encoding='utf-8'
            ) as tmp_file:
                tmp_path = tmp_file.name
                logger.debug(f"Writing to temporary file: {tmp_path}")

                # Write content to temporary file
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # Ensure data written to disk

                logger.debug(f"Content written to temporary file ({len(content)} bytes)")

            # Atomically replace target with temp file
            # os.replace() is atomic on both POSIX and Windows
            os.replace(tmp_path, target_path)

            logger.info(
                f"Atomic write completed successfully: {target_path} "
                f"({len(content)} bytes)"
            )

        except PermissionError as e:
            logger.error(f"Permission denied writing to {target_path}: {str(e)}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            raise PermissionError(
                f"Insufficient permissions to write to {target_path}. "
                f"Ensure the application has write access to {target_dir}"
            ) from e

        except OSError as e:
            logger.error(f"OS error during atomic write to {target_path}: {str(e)}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            raise IOError(f"Failed to write to {target_path}: {str(e)}") from e

        except Exception as e:
            logger.exception(f"Unexpected error during atomic write to {target_path}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            raise IOError(
                f"Unexpected error writing to {target_path}: {str(e)}"
            ) from e
