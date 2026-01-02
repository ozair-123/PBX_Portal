"""Configuration loader from environment variables."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Asterisk
    ASTERISK_PJSIP_CONFIG_PATH: str = "/etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf"
    ASTERISK_DIALPLAN_CONFIG_PATH: str = "/etc/asterisk/extensions.d/synergycall/generated_routing.conf"

    # Extension allocation
    EXTENSION_MIN: int = 1000
    EXTENSION_MAX: int = 1999

    # Default tenant
    DEFAULT_TENANT_ID: str = "a0000000-0000-0000-0000-000000000000"

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")


# Validate config on import
Config.validate()
