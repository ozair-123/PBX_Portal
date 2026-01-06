"""Apply service for synchronizing database state to Asterisk configuration."""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.user import User
from ..models.tenant import Tenant
from ..models.apply_audit_log import ApplyJob, ApplyStatus
from ..config import Config

logger = logging.getLogger(__name__)


class ApplyService:
    """
    Service for applying database configuration to Asterisk.

    This service orchestrates the complete apply workflow:
    1. Acquire PostgreSQL advisory lock (serialization)
    2. Validate configuration (check for conflicts, invalid data)
    3. Backup current configuration files
    4. Read all users and extensions from PostgreSQL database
    5. Generate new configuration files
    6. Write configuration files atomically
    7. Reload Asterisk modules
    8. Create audit log entry in PostgreSQL
    9. Rollback on failure (restore from backup)
    10. Release advisory lock
    """

    # PostgreSQL advisory lock ID for apply operations
    # Using a fixed integer to ensure all apply operations use the same lock
    APPLY_LOCK_ID = 123456789

    # Backup directory for configuration rollback
    BACKUP_DIR = Path("/var/backups/pbx_portal/config") if os.path.exists("/var") else Path("./backups/config")

    @staticmethod
    def validate_configuration(session: Session) -> Dict[str, Any]:
        """
        Validate configuration before applying.

        Checks:
        - Extension uniqueness within each tenant
        - No duplicate emails
        - All users have assigned extensions
        - Tenant extension ranges are valid

        Args:
            session: Database session

        Returns:
            dict: Validation result with keys:
                - valid: bool
                - errors: List[str] (validation errors)
                - warnings: List[str] (non-critical issues)
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Check for duplicate emails
        from sqlalchemy import func
        duplicate_emails = (
            session.query(User.email, func.count(User.id))
            .group_by(User.email)
            .having(func.count(User.id) > 1)
            .all()
        )
        if duplicate_emails:
            for email, count in duplicate_emails:
                errors.append(f"Duplicate email found: {email} ({count} users)")

        # Check extension uniqueness per tenant
        tenants = session.query(Tenant).all()
        for tenant in tenants:
            tenant_users = session.query(User).filter(User.tenant_id == tenant.id).all()

            # Check for duplicate extensions within tenant
            extension_counts: Dict[int, int] = {}
            for user in tenant_users:
                if user.extension:
                    extension_counts[user.extension] = extension_counts.get(user.extension, 0) + 1

            for ext, count in extension_counts.items():
                if count > 1:
                    errors.append(
                        f"Duplicate extension {ext} in tenant {tenant.name} ({count} users)"
                    )

            # Check for users without extensions
            users_without_extensions = [u for u in tenant_users if not u.extension]
            if users_without_extensions:
                for user in users_without_extensions:
                    errors.append(f"User {user.email} has no extension assigned")

            # Validate tenant extension range
            if tenant.ext_min >= tenant.ext_max:
                errors.append(
                    f"Invalid extension range for tenant {tenant.name}: "
                    f"{tenant.ext_min}-{tenant.ext_max}"
                )

            if tenant.ext_next > tenant.ext_max + 1:
                warnings.append(
                    f"Tenant {tenant.name} ext_next ({tenant.ext_next}) exceeds range "
                    f"({tenant.ext_min}-{tenant.ext_max})"
                )

        valid = len(errors) == 0

        logger.info(
            f"Configuration validation: {'PASSED' if valid else 'FAILED'} "
            f"({len(errors)} errors, {len(warnings)} warnings)"
        )

        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
        }

    @staticmethod
    def backup_configuration(config_files: List[str]) -> Optional[str]:
        """
        Backup configuration files before applying changes.

        Args:
            config_files: List of file paths to backup

        Returns:
            str: Backup directory path, or None if backup failed
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = ApplyService.BACKUP_DIR / timestamp

        try:
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)

            # Copy each config file to backup directory
            for config_file in config_files:
                if os.path.exists(config_file):
                    dest_file = backup_path / Path(config_file).name
                    shutil.copy2(config_file, dest_file)
                    logger.info(f"Backed up {config_file} to {dest_file}")

            logger.info(f"Configuration backup created at {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to backup configuration: {str(e)}")
            return None

    @staticmethod
    def rollback_configuration(backup_path: str, config_files: List[str]) -> bool:
        """
        Rollback configuration from backup.

        Args:
            backup_path: Path to backup directory
            config_files: List of config file paths to restore

        Returns:
            bool: True if rollback successful, False otherwise
        """
        try:
            backup_dir = Path(backup_path)

            if not backup_dir.exists():
                logger.error(f"Backup directory not found: {backup_path}")
                return False

            # Restore each config file from backup
            for config_file in config_files:
                backup_file = backup_dir / Path(config_file).name

                if backup_file.exists():
                    shutil.copy2(backup_file, config_file)
                    logger.info(f"Restored {config_file} from backup")
                else:
                    logger.warning(f"Backup file not found: {backup_file}")

            logger.info(f"Configuration rolled back from {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback configuration: {str(e)}")
            return False

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

            # Step 3: Sync PJSIP endpoints to MariaDB realtime
            logger.info("Syncing PJSIP endpoints to MariaDB")
            pjsip_sync_result = PJSIPRealtimeService.sync_endpoints(users_with_extensions)

            logger.info("Generating dialplan configuration")
            dialplan_config = DialplanGenerator.generate_config(users_with_extensions)

            # Step 4: Write dialplan configuration file
            dialplan_path = Config.ASTERISK_DIALPLAN_CONFIG_PATH

            logger.info(f"Writing dialplan config to {dialplan_path}")
            AtomicFileWriter.write_atomic(dialplan_config, dialplan_path)

            files_written = [dialplan_path]
            logger.info(
                f"Synced {pjsip_sync_result['endpoints_synced']} PJSIP endpoints to MariaDB, "
                f"wrote dialplan to {dialplan_path}"
            )

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
                logger.warning("Advisory lock released in success path")

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
            # Create failure audit log if not already created
            if audit_log is None:
                try:
                    # Rollback any pending transaction before creating audit log
                    session.rollback()

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

        finally:
            # CRITICAL: Always release the advisory lock, even if exception handling fails
            if lock_acquired:
                try:
                    # Ensure session is in a clean state before unlocking
                    session.rollback()

                    session.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": ApplyService.APPLY_LOCK_ID}
                    )
                    logger.warning("Advisory lock released in finally block")
                except Exception as unlock_error:
                    logger.error(
                        f"CRITICAL: Failed to release advisory lock in finally block: {str(unlock_error)}. "
                        f"Manual cleanup may be required: SELECT pg_advisory_unlock({ApplyService.APPLY_LOCK_ID});"
                    )
