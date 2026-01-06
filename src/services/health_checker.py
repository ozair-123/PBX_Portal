"""Health checker service for monitoring system components."""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from .ami_client import get_ami_client
from ..database import SessionLocal

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Health checker for monitoring system components.

    Checks:
    - PostgreSQL database connectivity
    - Asterisk AMI connectivity
    - MariaDB (PJSIP Realtime) connectivity (future)
    """

    @staticmethod
    def check_database() -> Dict[str, Any]:
        """
        Check PostgreSQL database health.

        Returns:
            dict: Health status with keys:
                - healthy: bool
                - latency_ms: float (query time in milliseconds)
                - error: str (if failed)
        """
        db: Session = SessionLocal()
        start_time = datetime.utcnow()

        try:
            # Execute simple query to test connectivity
            result = db.execute(text("SELECT 1")).scalar()

            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000

            if result == 1:
                return {
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                }
            else:
                return {
                    "healthy": False,
                    "error": "Unexpected query result",
                }

        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
            }
        finally:
            db.close()

    @staticmethod
    async def check_asterisk() -> Dict[str, Any]:
        """
        Check Asterisk AMI health.

        Returns:
            dict: Health status with keys:
                - healthy: bool
                - version: str (Asterisk version)
                - error: str (if failed)
        """
        ami_client = get_ami_client()

        try:
            status = await ami_client.check_status()
            return status

        except Exception as e:
            logger.error(f"Asterisk health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
            }

    @staticmethod
    async def check_all() -> Dict[str, Any]:
        """
        Check health of all system components.

        Returns:
            dict: Comprehensive health status with keys:
                - overall_healthy: bool (True if all components healthy)
                - timestamp: str (ISO format)
                - components: dict (individual component statuses)
        """
        # Check database (sync)
        db_status = HealthChecker.check_database()

        # Check Asterisk (async)
        asterisk_status = await HealthChecker.check_asterisk()

        # Determine overall health
        overall_healthy = (
            db_status.get("healthy", False) and
            asterisk_status.get("healthy", False)
        )

        return {
            "overall_healthy": overall_healthy,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": db_status,
                "asterisk": asterisk_status,
            },
        }


# Convenience function for FastAPI endpoint
async def get_health_status() -> Dict[str, Any]:
    """
    Get comprehensive health status (FastAPI dependency/endpoint).

    Returns:
        dict: Health status for all components
    """
    return await HealthChecker.check_all()
