"""Extension allocation service with concurrency-safe retry logic."""

import secrets
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from ..models.extension import Extension
from ..config import Config

logger = logging.getLogger(__name__)


def generate_sip_secret(length: int = 16) -> str:
    """
    Generate a cryptographically secure SIP secret.

    Args:
        length: Length parameter for token generation (default: 16)

    Returns:
        URL-safe random token suitable for SIP authentication
    """
    return secrets.token_urlsafe(length)


def allocate_extension(session: Session, user_id: str, max_retries: int = 5) -> Extension:
    """
    Allocate the next available extension number for a user with concurrency-safe retry logic.

    This function implements race-condition safe allocation by:
    1. Finding the minimum available extension number in the configured range
    2. Attempting to insert with UNIQUE constraint enforcement
    3. Retrying on conflict (IntegrityError) up to max_retries times

    Args:
        session: SQLAlchemy database session
        user_id: UUID of the user to allocate extension for
        max_retries: Maximum retry attempts on conflict (default: 5)

    Returns:
        Extension: The successfully allocated Extension object

    Raises:
        ValueError: If extension pool is exhausted (all 1000 extensions allocated)
        RuntimeError: If max retries exceeded due to high contention
    """
    extension_range_start = Config.EXTENSION_MIN
    extension_range_end = Config.EXTENSION_MAX

    for attempt in range(max_retries):
        # Find the minimum available extension number
        # This query finds the smallest number in range that's not yet allocated
        query = text("""
            SELECT COALESCE(
                (
                    SELECT MIN(candidate.number)
                    FROM generate_series(:start, :end) AS candidate(number)
                    LEFT JOIN extensions ON extensions.number = candidate.number
                    WHERE extensions.number IS NULL
                ),
                NULL
            ) AS available_extension
        """)

        result = session.execute(
            query,
            {"start": extension_range_start, "end": extension_range_end}
        )
        available_number = result.scalar()

        if available_number is None:
            logger.error(
                f"Extension pool exhausted: all extensions in range "
                f"{extension_range_start}-{extension_range_end} are allocated"
            )
            raise ValueError(
                f"Extension pool exhausted: no available extensions in range "
                f"{extension_range_start}-{extension_range_end}"
            )

        # Generate SIP secret for this extension
        secret = generate_sip_secret()

        # Attempt to create the extension with UNIQUE constraint enforcement
        try:
            extension = Extension(
                number=available_number,
                user_id=user_id,
                secret=secret
            )
            session.add(extension)
            session.flush()  # Flush to DB to trigger UNIQUE constraint check

            logger.info(
                f"Successfully allocated extension {available_number} for user {user_id} "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            return extension

        except IntegrityError as e:
            # Another transaction allocated this extension concurrently
            session.rollback()
            logger.warning(
                f"Extension {available_number} conflict on attempt {attempt + 1}/{max_retries} "
                f"for user {user_id}: {str(e)}"
            )

            if attempt == max_retries - 1:
                # Last retry failed
                logger.error(
                    f"Max retries ({max_retries}) exceeded for extension allocation "
                    f"for user {user_id}. High contention detected."
                )
                raise RuntimeError(
                    f"Failed to allocate extension after {max_retries} attempts due to high "
                    f"contention. Please try again."
                )

            # Continue to next retry
            continue

    # Should never reach here due to the raise in the loop
    raise RuntimeError("Extension allocation failed unexpectedly")
