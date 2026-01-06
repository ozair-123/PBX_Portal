"""Asterisk Manager Interface (AMI) client for PBX management."""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AMIClient:
    """
    Asterisk Manager Interface client.

    Provides methods to connect to Asterisk AMI and execute commands:
    - Reload modules (pjsip, dialplan, voicemail)
    - Check Asterisk status
    - Execute CLI commands
    - Monitor events (future enhancement)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        """
        Initialize AMI client.

        Args:
            host: Asterisk server hostname/IP (defaults to env ASTERISK_AMI_HOST)
            port: AMI port (defaults to env ASTERISK_AMI_PORT or 5038)
            username: AMI username (defaults to env ASTERISK_AMI_USER)
            secret: AMI secret (defaults to env ASTERISK_AMI_SECRET)
        """
        self.host = host or os.getenv("ASTERISK_AMI_HOST", "localhost")
        self.port = int(port or os.getenv("ASTERISK_AMI_PORT", 5038))
        self.username = username or os.getenv("ASTERISK_AMI_USER", "admin")
        self.secret = secret or os.getenv("ASTERISK_AMI_SECRET")

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False

    async def connect(self) -> bool:
        """
        Connect to Asterisk AMI.

        Returns:
            bool: True if connected successfully, False otherwise
        """
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0,
            )

            # Read Asterisk greeting
            greeting = await self._read_response()
            logger.info(f"AMI connected: {greeting.get('Response', 'Unknown')}")

            # Authenticate
            await self._send_action({
                "Action": "Login",
                "Username": self.username,
                "Secret": self.secret,
            })

            response = await self._read_response()

            if response.get("Response") == "Success":
                self.connected = True
                logger.info(f"AMI authenticated as {self.username}")
                return True
            else:
                logger.error(f"AMI authentication failed: {response}")
                return False

        except asyncio.TimeoutError:
            logger.error(f"AMI connection timeout to {self.host}:{self.port}")
            return False
        except Exception as e:
            logger.error(f"AMI connection error: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Asterisk AMI."""
        if self.writer:
            try:
                await self._send_action({"Action": "Logoff"})
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.warning(f"AMI disconnect error: {str(e)}")
            finally:
                self.connected = False
                logger.info("AMI disconnected")

    async def reload_pjsip(self) -> Dict[str, Any]:
        """
        Reload PJSIP module (apply SIP endpoint changes).

        Returns:
            dict: Response from Asterisk
        """
        return await self.execute_command("module reload res_pjsip.so")

    async def reload_dialplan(self) -> Dict[str, Any]:
        """
        Reload dialplan (apply routing changes).

        Returns:
            dict: Response from Asterisk
        """
        return await self.execute_command("dialplan reload")

    async def reload_voicemail(self) -> Dict[str, Any]:
        """
        Reload voicemail (apply voicemail changes).

        Returns:
            dict: Response from Asterisk
        """
        return await self.execute_command("module reload app_voicemail.so")

    async def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute Asterisk CLI command via AMI.

        Args:
            command: CLI command to execute (e.g., "core show version")

        Returns:
            dict: Response from Asterisk with keys:
                - success: bool
                - output: str (command output)
                - error: str (if failed)
        """
        if not self.connected:
            await self.connect()

        try:
            await self._send_action({
                "Action": "Command",
                "Command": command,
            })

            response = await self._read_response()

            if response.get("Response") == "Success":
                # Read command output (follows the response)
                output_lines = []
                while True:
                    line = await self.reader.readline()
                    decoded_line = line.decode("utf-8").strip()
                    if not decoded_line or decoded_line.startswith("--END COMMAND--"):
                        break
                    output_lines.append(decoded_line)

                return {
                    "success": True,
                    "output": "\n".join(output_lines),
                }
            else:
                return {
                    "success": False,
                    "error": response.get("Message", "Unknown error"),
                }

        except Exception as e:
            logger.error(f"AMI command execution error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    async def check_status(self) -> Dict[str, Any]:
        """
        Check Asterisk status (uptime, version, etc.).

        Returns:
            dict: Status information with keys:
                - healthy: bool
                - version: str
                - uptime: str
                - error: str (if failed)
        """
        try:
            result = await self.execute_command("core show version")

            if result["success"]:
                return {
                    "healthy": True,
                    "version": result["output"].split("\n")[0] if result["output"] else "Unknown",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "healthy": False,
                    "error": result.get("error", "Unknown error"),
                }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _send_action(self, action: Dict[str, str]) -> None:
        """
        Send AMI action to Asterisk.

        Args:
            action: Dictionary of action fields (e.g., {"Action": "Login", ...})
        """
        message = ""
        for key, value in action.items():
            message += f"{key}: {value}\r\n"
        message += "\r\n"  # Terminate with blank line

        self.writer.write(message.encode("utf-8"))
        await self.writer.drain()

    async def _read_response(self) -> Dict[str, str]:
        """
        Read AMI response from Asterisk.

        Returns:
            dict: Parsed response fields
        """
        response = {}

        while True:
            line = await self.reader.readline()
            decoded_line = line.decode("utf-8").strip()

            if not decoded_line:
                # Empty line indicates end of response
                break

            if ":" in decoded_line:
                key, value = decoded_line.split(":", 1)
                response[key.strip()] = value.strip()

        return response


# Singleton instance (optional - for convenience)
_ami_client: Optional[AMIClient] = None


def get_ami_client() -> AMIClient:
    """
    Get singleton AMI client instance.

    Returns:
        AMIClient: Shared AMI client instance
    """
    global _ami_client
    if _ami_client is None:
        _ami_client = AMIClient()
    return _ami_client
