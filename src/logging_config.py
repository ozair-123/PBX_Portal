"""Logging configuration for PBX Control Portal."""

import logging
import sys

from .config import Config


def setup_logging():
    """Configure application logging."""
    # Get log level from config
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set levels for specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {Config.LOG_LEVEL}")


# Setup logging on import
setup_logging()
