"""Asterisk Manager Interface (AMI) client stub."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AMIClient:
    """
    Mock AMI client for testing.

    In production, this would connect to Asterisk via AMI protocol.
    """

    def __init__(self, host: str = "localhost", port: int = 5038):
        """Initialize AMI client."""
        self.host = host
        self.port = port
        self.connected = False

    def connect(self, username: str = "admin", password: str = "secret") -> bool:
        """
        Connect to AMI.

        Args:
            username: AMI username
            password: AMI password

        Returns:
            True if connected successfully
        """
        logger.info(f"AMI: Simulating connection to {self.host}:{self.port}")
        self.connected = True
        return True

    def disconnect(self):
        """Disconnect from AMI."""
        logger.info("AMI: Disconnecting")
        self.connected = False

    def reload(self, module: Optional[str] = None) -> bool:
        """
        Reload Asterisk module or all modules.

        Args:
            module: Optional module name (e.g., "dialplan")

        Returns:
            True if reload successful
        """
        target = module or "all"
        logger.info(f"AMI: Simulating reload of {target}")
        return True

    def command(self, cmd: str) -> str:
        """
        Execute arbitrary Asterisk CLI command.

        Args:
            cmd: CLI command string

        Returns:
            Command output
        """
        logger.info(f"AMI: Simulating command: {cmd}")
        return f"OK: {cmd}"

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.connected:
            self.disconnect()


def get_ami_client() -> AMIClient:
    """
    Get an AMI client instance.

    Returns:
        AMIClient instance
    """
    return AMIClient()
