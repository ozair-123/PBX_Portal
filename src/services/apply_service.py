"""Apply service for synchronizing database state to Asterisk configuration."""

import logging
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.user import User
from ..models.apply_audit_log import ApplyAuditLog
from ..config import Config
from ..config_generator.pjsip_generator import PJSIPGenerator
from ..config_generator.dialplan_generator import DialplanGenerator
from ..config_generator.atomic_writer import AtomicFileWriter
from ..asterisk.reloader import AsteriskReloader

logger = logging.getLogger(__name__)


class ApplyService:
    """
    Service for applying database configuration to Asterisk.

    This service orchestrates the complete apply workflow:
    1. Acquire PostgreSQL advisory lock (serialization)
    2. Read all users and extensions from database
    3. Generate PJSIP and dialplan configurations
    4. Write configuration files atomically
    5. Reload Asterisk modules
    6. Create audit log entry
    7. Release advisory lock
    """

    # PostgreSQL advisory lock ID for apply operations
    # Using a fixed integer to ensure all apply operations use the same lock
    APPLY_LOCK_ID = 123456789

    @staticmethod
    def apply_configuration(session: Session, triggered_by: str) -> Dict[str, Any]:
        """
        Apply current database configuration to Asterisk.

        This method is serialized using PostgreSQL advisory locks to prevent
        concurrent apply operations from conflicting.

        Args:
            session: SQLAlchemy database session
            triggered_by: Username or identifier of who triggered the apply

        Returns:
            Dict containing apply results:
            {
                "audit_log_id": str,
                "files_written": List[str],
                "reload_results": Dict[str, Any],
                "users_applied": int,
                "extensions_generated": int,
                "outcome": str
            }

        Raises:
            RuntimeError: If apply operation fails at any step
            PermissionError: If insufficient permissions to write files or reload Asterisk
        """
        logger.info(f"Starting apply configuration triggered by: {triggered_by}")

        # Track whether we acquired the lock (for cleanup)
        lock_acquired = False
        audit_log = None

        try:
            # Step 1: Acquire PostgreSQL advisory lock (serialize apply operations)
            logger.info(f"Attempting to acquire advisory lock {ApplyService.APPLY_LOCK_ID}")
            lock_result = session.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": ApplyService.APPLY_LOCK_ID}
            ).scalar()

            if not lock_result:
                logger.warning("Another apply operation is in progress (lock conflict)")
                raise RuntimeError(
                    "Another apply operation is currently in progress. "
                    "Please wait and try again."
                )

            lock_acquired = True
            logger.info("Advisory lock acquired successfully")

            # Step 2: Read all users with their extensions
            logger.info("Reading users and extensions from database")
            users = session.query(User).all()

            users_with_extensions = []
            for user in users:
                user_dict = {
                    "id": str(user.id),
                    "tenant_id": str(user.tenant_id),
                    "name": user.name,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                    "extension": None
                }

                if user.extension:
                    user_dict["extension"] = {
                        "id": str(user.extension.id),
                        "number": user.extension.number,
                        "secret": user.extension.secret,
                        "created_at": user.extension.created_at.isoformat()
                    }

                users_with_extensions.append(user_dict)

            users_count = len(users_with_extensions)
            extensions_count = sum(1 for u in users_with_extensions if u.get("extension"))

            logger.info(
                f"Loaded {users_count} users with {extensions_count} extensions from database"
            )

            # Step 3: Generate configuration files
            logger.info("Generating PJSIP configuration")
            pjsip_config = PJSIPGenerator.generate_config(users_with_extensions)

            logger.info("Generating dialplan configuration")
            dialplan_config = DialplanGenerator.generate_config(users_with_extensions)

            # Step 4: Write configuration files atomically
            pjsip_path = Config.ASTERISK_PJSIP_CONFIG_PATH
            dialplan_path = Config.ASTERISK_DIALPLAN_CONFIG_PATH

            logger.info(f"Writing PJSIP config to {pjsip_path}")
            AtomicFileWriter.write_atomic(pjsip_config, pjsip_path)

            logger.info(f"Writing dialplan config to {dialplan_path}")
            AtomicFileWriter.write_atomic(dialplan_config, dialplan_path)

            files_written = [pjsip_path, dialplan_path]
            logger.info(f"Configuration files written successfully: {files_written}")

            # Step 5: Reload Asterisk modules
            logger.info("Reloading Asterisk PJSIP module")
            pjsip_reload_result = AsteriskReloader.reload_pjsip()

            logger.info("Reloading Asterisk dialplan")
            dialplan_reload_result = AsteriskReloader.reload_dialplan()

            reload_results = {
                "pjsip": pjsip_reload_result,
                "dialplan": dialplan_reload_result
            }

            # Check if any reload failed
            reload_success = (
                pjsip_reload_result.get("success", False) and
                dialplan_reload_result.get("success", False)
            )

            if not reload_success:
                logger.error(f"Asterisk reload failed: {reload_results}")
                outcome = "failure"
                error_details = (
                    f"PJSIP: {pjsip_reload_result.get('stderr', 'Unknown error')}, "
                    f"Dialplan: {dialplan_reload_result.get('stderr', 'Unknown error')}"
                )
            else:
                logger.info("Asterisk modules reloaded successfully")
                outcome = "success"
                error_details = None

            # Step 6: Create audit log entry
            audit_log = ApplyAuditLog(
                triggered_at=datetime.utcnow(),
                triggered_by=triggered_by,
                outcome=outcome,
                error_details=error_details,
                files_written=files_written,
                reload_results=reload_results
            )
            session.add(audit_log)
            session.commit()

            logger.info(f"Audit log created: {audit_log.id}")

            # Step 7: Release advisory lock
            if lock_acquired:
                session.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": ApplyService.APPLY_LOCK_ID}
                )
                lock_acquired = False
                logger.info("Advisory lock released")

            result = {
                "audit_log_id": str(audit_log.id),
                "files_written": files_written,
                "reload_results": reload_results,
                "users_applied": users_count,
                "extensions_generated": extensions_count,
                "outcome": outcome
            }

            if outcome == "failure":
                logger.error(f"Apply completed with failures: {result}")
                raise RuntimeError(
                    f"Apply operation completed but Asterisk reload failed: {error_details}"
                )

            logger.info(f"Apply configuration completed successfully: {result}")
            return result

        except Exception as e:
            # Ensure lock is released on any error
            if lock_acquired:
                try:
                    session.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": ApplyService.APPLY_LOCK_ID}
                    )
                    logger.info("Advisory lock released after error")
                except Exception as unlock_error:
                    logger.error(f"Failed to release advisory lock: {str(unlock_error)}")

            # Create failure audit log if not already created
            if audit_log is None:
                try:
                    audit_log = ApplyAuditLog(
                        triggered_at=datetime.utcnow(),
                        triggered_by=triggered_by,
                        outcome="failure",
                        error_details=str(e),
                        files_written=None,
                        reload_results=None
                    )
                    session.add(audit_log)
                    session.commit()
                    logger.info(f"Failure audit log created: {audit_log.id}")
                except Exception as audit_error:
                    logger.error(f"Failed to create failure audit log: {str(audit_error)}")

            logger.exception(f"Apply configuration failed: {str(e)}")
            raise
