"""Asterisk module reloader using subprocess."""

import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AsteriskReloader:
    """
    Reloads Asterisk modules using subprocess to execute asterisk CLI commands.

    Uses subprocess.run() to execute 'asterisk -rx' commands locally.
    This assumes the application runs on the same server as Asterisk.
    """

    @staticmethod
    def reload_pjsip() -> Dict[str, Any]:
        """
        Reload Asterisk PJSIP module.

        Executes: asterisk -rx "module reload res_pjsip.so"

        Returns:
            Dict containing reload result:
            {
                "command": str,
                "exit_code": int,
                "stdout": str,
                "stderr": str,
                "success": bool
            }

        Raises:
            FileNotFoundError: If asterisk command is not found
            PermissionError: If insufficient permissions to execute asterisk command
        """
        command = ["asterisk", "-rx", "module reload res_pjsip.so"]
        logger.info(f"Reloading PJSIP module: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=False  # Don't raise exception on non-zero exit
            )

            success = result.returncode == 0

            if success:
                logger.info(f"PJSIP reload successful: {result.stdout.strip()}")
            else:
                logger.error(
                    f"PJSIP reload failed (exit {result.returncode}): "
                    f"stdout={result.stdout.strip()}, stderr={result.stderr.strip()}"
                )

            return {
                "command": " ".join(command),
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": success
            }

        except FileNotFoundError:
            logger.error("Asterisk command not found - is Asterisk installed?")
            raise FileNotFoundError(
                "Asterisk command not found. Ensure Asterisk is installed and in PATH."
            )

        except PermissionError as e:
            logger.error(f"Permission denied executing asterisk command: {str(e)}")
            raise PermissionError(
                "Insufficient permissions to execute asterisk command. "
                "Ensure the application user can run asterisk CLI."
            ) from e

        except subprocess.TimeoutExpired:
            logger.error("PJSIP reload timed out after 30 seconds")
            return {
                "command": " ".join(command),
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "success": False
            }

        except Exception as e:
            logger.exception(f"Unexpected error reloading PJSIP: {str(e)}")
            raise RuntimeError(f"Failed to reload PJSIP: {str(e)}") from e

    @staticmethod
    def reload_dialplan() -> Dict[str, Any]:
        """
        Reload Asterisk dialplan.

        Executes: asterisk -rx "dialplan reload"

        Returns:
            Dict containing reload result:
            {
                "command": str,
                "exit_code": int,
                "stdout": str,
                "stderr": str,
                "success": bool
            }

        Raises:
            FileNotFoundError: If asterisk command is not found
            PermissionError: If insufficient permissions to execute asterisk command
        """
        command = ["asterisk", "-rx", "dialplan reload"]
        logger.info(f"Reloading dialplan: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=False  # Don't raise exception on non-zero exit
            )

            success = result.returncode == 0

            if success:
                logger.info(f"Dialplan reload successful: {result.stdout.strip()}")
            else:
                logger.error(
                    f"Dialplan reload failed (exit {result.returncode}): "
                    f"stdout={result.stdout.strip()}, stderr={result.stderr.strip()}"
                )

            return {
                "command": " ".join(command),
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": success
            }

        except FileNotFoundError:
            logger.error("Asterisk command not found - is Asterisk installed?")
            raise FileNotFoundError(
                "Asterisk command not found. Ensure Asterisk is installed and in PATH."
            )

        except PermissionError as e:
            logger.error(f"Permission denied executing asterisk command: {str(e)}")
            raise PermissionError(
                "Insufficient permissions to execute asterisk command. "
                "Ensure the application user can run asterisk CLI."
            ) from e

        except subprocess.TimeoutExpired:
            logger.error("Dialplan reload timed out after 30 seconds")
            return {
                "command": " ".join(command),
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "success": False
            }

        except Exception as e:
            logger.exception(f"Unexpected error reloading dialplan: {str(e)}")
            raise RuntimeError(f"Failed to reload dialplan: {str(e)}") from e
