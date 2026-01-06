"""Enhanced apply service with complete safe apply workflow."""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.user import User
from ..models.tenant import Tenant
from ..models.apply_audit_log import ApplyJob, ApplyStatus
from ..config_generator.dialplan_generator import DialplanGenerator
from ..services.ami_client import get_ami_client
from .apply_service import ApplyService

logger = logging.getLogger(__name__)


class EnhancedApplyService:
    """
    Enhanced apply service with complete safe apply workflow.

    Workflow:
    1. Acquire PostgreSQL advisory lock
    2. Validate configuration
    3. Backup current configs
    4. Generate new configs
    5. Write configs atomically
    6. Reload Asterisk (AMI)
    7. Rollback on failure
    8. Release lock
    """

    DIALPLAN_PATH = Path("/etc/asterisk/extensions_custom.conf")

    @staticmethod
    def apply_configuration_safe(
        session: Session,
        actor_id: UUID,
        tenant_id: Optional[UUID] = None,
        force: bool = False,
    ) -> ApplyJob:
        """
        Safe apply configuration with validation, backup, and rollback.

        Args:
            session: Database session
            actor_id: ID of user triggering apply
            tenant_id: Optional tenant ID (apply for specific tenant only)
            force: Force apply even if validation fails

        Returns:
            ApplyJob: Apply job record with status

        Raises:
            RuntimeError: If another apply is in progress or apply fails
        """
        lock_acquired = False
        backup_path = None

        # Create apply job record
        apply_job = ApplyJob(
            tenant_id=tenant_id,
            actor_id=actor_id,
            status=ApplyStatus.PENDING,
        )
        session.add(apply_job)
        session.flush()

        try:
            # Step 1: Acquire advisory lock
            logger.info(f"Apply job {apply_job.id}: Acquiring lock")
            lock_result = session.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": ApplyService.APPLY_LOCK_ID}
            ).scalar()

            if not lock_result:
                apply_job.fail("Another apply operation is in progress")
                session.commit()
                raise RuntimeError("Another apply operation is in progress")

            lock_acquired = True
            apply_job.start()
            session.commit()

            # Step 2: Validate configuration
            logger.info(f"Apply job {apply_job.id}: Validating configuration")
            validation = ApplyService.validate_configuration(session)

            if not validation["valid"] and not force:
                error_msg = f"Configuration validation failed: {', '.join(validation['errors'])}"
                apply_job.fail(error_msg)
                session.commit()
                raise RuntimeError(error_msg)

            if validation["warnings"]:
                logger.warning(f"Validation warnings: {validation['warnings']}")

            # Step 3: Load data
            logger.info(f"Apply job {apply_job.id}: Loading configuration data")
            users = session.query(User).all()
            tenants = session.query(Tenant).all()

            # Query DID assignments with phone number details
            from src.models import PhoneNumber, DIDAssignment, PhoneNumberStatus
            did_assignments = session.query(DIDAssignment).join(
                PhoneNumber,
                DIDAssignment.phone_number_id == PhoneNumber.id
            ).filter(
                PhoneNumber.status == PhoneNumberStatus.ASSIGNED
            ).all()

            if tenant_id:
                users = [u for u in users if u.tenant_id == tenant_id]
                tenants = [t for t in tenants if t.id == tenant_id]
                # Filter DID assignments by tenant
                did_assignments = [a for a in did_assignments if a.phone_number.tenant_id == tenant_id]

            # Convert to dicts for generators
            users_data = []
            for user in users:
                users_data.append({
                    "id": str(user.id),
                    "tenant_id": str(user.tenant_id),
                    "name": user.name,
                    "email": user.email,
                    "extension": user.extension,
                    "role": user.role.value,
                    "status": user.status.value,
                    "dnd_enabled": user.dnd_enabled,
                    "call_forward_destination": user.call_forward_destination,
                    "voicemail_enabled": user.voicemail_enabled,
                })

            tenants_data = []
            for tenant in tenants:
                tenants_data.append({
                    "id": str(tenant.id),
                    "name": tenant.name,
                    "ext_min": tenant.ext_min,
                    "ext_max": tenant.ext_max,
                    "ext_next": tenant.ext_next,
                })

            # Convert DID assignments to dicts for dialplan generation
            did_assignments_data = []
            for assignment in did_assignments:
                phone_number = assignment.phone_number
                tenant = next((t for t in tenants if t.id == phone_number.tenant_id), None)

                assignment_dict = {
                    "number": phone_number.number,
                    "assigned_type": assignment.assigned_type.value,
                    "assigned_id": str(assignment.assigned_id) if assignment.assigned_id else None,
                    "assigned_value": assignment.assigned_value,
                    "tenant_id": str(phone_number.tenant_id) if phone_number.tenant_id else None,
                }

                # For USER assignments, lookup extension and tenant context
                if assignment.assigned_type.value == "USER" and assignment.assigned_id:
                    user = next((u for u in users if u.id == assignment.assigned_id), None)
                    if user and tenant:
                        assignment_dict["extension"] = user.extension
                        assignment_dict["tenant_context"] = f"tenant-{tenant.name.lower().replace(' ', '-')}"

                did_assignments_data.append(assignment_dict)

            logger.info(f"Loaded {len(did_assignments_data)} DID assignments")

            # Step 4: Backup current configs
            logger.info(f"Apply job {apply_job.id}: Backing up current configuration")
            config_files = [str(EnhancedApplyService.DIALPLAN_PATH)]
            backup_path = ApplyService.backup_configuration(config_files)

            if not backup_path:
                logger.warning("Backup failed, continuing without backup")

            # Step 5: Generate new dialplan
            logger.info(f"Apply job {apply_job.id}: Generating dialplan configuration")
            dialplan_config = DialplanGenerator.generate_config(
                users_with_extensions=users_data,
                tenants=tenants_data,
                did_assignments=did_assignments_data,
            )

            # Step 6: Write configuration
            logger.info(f"Apply job {apply_job.id}: Writing configuration files")
            EnhancedApplyService.DIALPLAN_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write (write to temp, then move)
            temp_path = EnhancedApplyService.DIALPLAN_PATH.with_suffix(".tmp")
            temp_path.write_text(dialplan_config)
            temp_path.replace(EnhancedApplyService.DIALPLAN_PATH)

            # Step 7: Reload Asterisk via AMI
            logger.info(f"Apply job {apply_job.id}: Reloading Asterisk")
            reload_success = asyncio.run(EnhancedApplyService._reload_asterisk())

            if not reload_success:
                # Rollback on reload failure
                logger.error(f"Apply job {apply_job.id}: Asterisk reload failed, rolling back")
                if backup_path:
                    ApplyService.rollback_configuration(backup_path, config_files)
                apply_job.fail("Asterisk reload failed")
                session.commit()
                raise RuntimeError("Asterisk reload failed")

            # Success!
            diff_summary = f"Applied {len(users_data)} users across {len(tenants_data)} tenant(s)"
            apply_job.succeed(diff_summary)
            apply_job.config_files_json = {"dialplan": str(EnhancedApplyService.DIALPLAN_PATH)}
            session.commit()

            logger.info(f"Apply job {apply_job.id}: Completed successfully")
            return apply_job

        except Exception as e:
            logger.exception(f"Apply job {apply_job.id}: Failed with error")

            # Rollback configuration if we have a backup
            if backup_path:
                logger.info(f"Apply job {apply_job.id}: Rolling back configuration")
                ApplyService.rollback_configuration(backup_path, [str(EnhancedApplyService.DIALPLAN_PATH)])

            # Update job status
            if apply_job.status != ApplyStatus.FAILED:
                apply_job.fail(str(e))
                session.commit()

            raise

        finally:
            # Always release the lock
            if lock_acquired:
                session.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": ApplyService.APPLY_LOCK_ID}
                )
                logger.info(f"Apply job {apply_job.id}: Released lock")

    @staticmethod
    async def _reload_asterisk() -> bool:
        """
        Reload Asterisk dialplan via AMI.

        Returns:
            bool: True if reload successful, False otherwise
        """
        ami = get_ami_client()

        try:
            # Connect to AMI
            connected = await ami.connect()
            if not connected:
                logger.error("Failed to connect to Asterisk AMI")
                return False

            # Reload dialplan
            result = await ami.reload_dialplan()

            # Disconnect
            await ami.disconnect()

            return result.get("success", False)

        except Exception as e:
            logger.error(f"Error reloading Asterisk: {str(e)}")
            return False

    @staticmethod
    def get_apply_job(session: Session, job_id: UUID) -> Optional[ApplyJob]:
        """Get apply job by ID."""
        return session.query(ApplyJob).filter(ApplyJob.id == job_id).first()

    @staticmethod
    def list_apply_jobs(
        session: Session,
        tenant_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        List apply jobs with filtering and pagination.

        Args:
            session: Database session
            tenant_id: Filter by tenant ID
            status: Filter by status
            page: Page number
            page_size: Items per page

        Returns:
            dict: {jobs: List[ApplyJob], total: int, page: int, page_size: int}
        """
        query = session.query(ApplyJob)

        # Apply filters
        if tenant_id:
            query = query.filter(ApplyJob.tenant_id == tenant_id)
        if status:
            query = query.filter(ApplyJob.status == ApplyStatus[status])

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        jobs = query.order_by(ApplyJob.created_at.desc()).offset(offset).limit(page_size).all()

        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
