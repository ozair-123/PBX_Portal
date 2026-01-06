"""
Audit logging service for centralized change tracking.

This service provides a consistent interface for logging all CRUD operations
across the application, ensuring complete audit trail compliance.
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog, AuditAction


class AuditService:
    """
    Centralized audit logging service.

    Use this service to log all changes to entities for compliance
    and troubleshooting. Audit logs are immutable and append-only.
    """

    @staticmethod
    def log_create(
        session: Session,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        after_state: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log entity creation.

        Args:
            session: Database session
            actor_id: ID of user performing the action
            entity_type: Type of entity (e.g., "User", "Device", "DID")
            entity_id: ID of the created entity
            after_state: Complete entity state after creation
            tenant_id: Tenant ID (if applicable)
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            Created AuditLog entry

        Example:
            >>> audit_service.log_create(
            ...     session=session,
            ...     actor_id=current_user.id,
            ...     entity_type="User",
            ...     entity_id=new_user.id,
            ...     after_state={"email": "john@example.com", "name": "John"},
            ...     tenant_id=tenant.id,
            ...     source_ip="192.168.1.100"
            ... )
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=None,  # NULL for CREATE
            after_json=after_state,
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        session.add(audit_log)
        session.flush()  # Get ID without committing
        return audit_log

    @staticmethod
    def log_update(
        session: Session,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log entity update.

        Args:
            session: Database session
            actor_id: ID of user performing the action
            entity_type: Type of entity
            entity_id: ID of the updated entity
            before_state: Entity state before update
            after_state: Entity state after update
            tenant_id: Tenant ID (if applicable)
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            Created AuditLog entry

        Example:
            >>> audit_service.log_update(
            ...     session=session,
            ...     actor_id=current_user.id,
            ...     entity_type="User",
            ...     entity_id=user.id,
            ...     before_state={"status": "active", "name": "John"},
            ...     after_state={"status": "suspended", "name": "John"},
            ...     tenant_id=tenant.id
            ... )
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before_state,
            after_json=after_state,
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        session.add(audit_log)
        session.flush()
        return audit_log

    @staticmethod
    def log_delete(
        session: Session,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        before_state: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log entity deletion.

        Args:
            session: Database session
            actor_id: ID of user performing the action
            entity_type: Type of entity
            entity_id: ID of the deleted entity
            before_state: Entity state before deletion
            tenant_id: Tenant ID (if applicable)
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            Created AuditLog entry

        Example:
            >>> audit_service.log_delete(
            ...     session=session,
            ...     actor_id=current_user.id,
            ...     entity_type="Device",
            ...     entity_id=device.id,
            ...     before_state={"label": "Desk Phone", "enabled": True},
            ...     tenant_id=tenant.id
            ... )
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before_state,
            after_json=None,  # NULL for DELETE
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        session.add(audit_log)
        session.flush()
        return audit_log

    @staticmethod
    def log_login(
        session: Session,
        actor_id: UUID,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log user login event.

        Args:
            session: Database session
            actor_id: ID of user logging in
            tenant_id: Tenant ID (if applicable)
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            Created AuditLog entry
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=AuditAction.LOGIN,
            entity_type="User",
            entity_id=actor_id,
            before_json=None,
            after_json={"timestamp": datetime.utcnow().isoformat()},
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        session.add(audit_log)
        session.flush()
        return audit_log

    @staticmethod
    def log_logout(
        session: Session,
        actor_id: UUID,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log user logout event.

        Args:
            session: Database session
            actor_id: ID of user logging out
            tenant_id: Tenant ID (if applicable)
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            Created AuditLog entry
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=AuditAction.LOGOUT,
            entity_type="User",
            entity_id=actor_id,
            before_json=None,
            after_json={"timestamp": datetime.utcnow().isoformat()},
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        session.add(audit_log)
        session.flush()
        return audit_log

    @staticmethod
    def log_apply(
        session: Session,
        actor_id: UUID,
        apply_job_id: UUID,
        status: str,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log apply operation.

        Args:
            session: Database session
            actor_id: ID of user triggering apply
            apply_job_id: ID of the ApplyJob
            status: Apply status (PENDING, RUNNING, SUCCESS, FAILED, ROLLED_BACK)
            tenant_id: Tenant ID (if applicable)
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            Created AuditLog entry
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=AuditAction.APPLY,
            entity_type="ApplyJob",
            entity_id=apply_job_id,
            before_json=None,
            after_json={"status": status, "timestamp": datetime.utcnow().isoformat()},
            source_ip=source_ip,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        session.add(audit_log)
        session.flush()
        return audit_log

    @staticmethod
    def entity_to_dict(entity: Any, exclude_fields: Optional[list] = None) -> Dict[str, Any]:
        """
        Convert SQLAlchemy entity to dictionary for audit logging.

        Excludes sensitive fields like passwords and large binary data.

        Args:
            entity: SQLAlchemy model instance
            exclude_fields: Additional fields to exclude

        Returns:
            Dictionary representation of entity

        Example:
            >>> user = User(id=uuid4(), email="john@example.com", password_hash="...")
            >>> audit_service.entity_to_dict(user, exclude_fields=["password_hash"])
            {'id': '...', 'email': 'john@example.com'}
        """
        if exclude_fields is None:
            exclude_fields = []

        # Default fields to exclude (sensitive data)
        default_exclude = [
            "password_hash",
            "sip_password_encrypted",
            "voicemail_pin_hash",
            "_sa_instance_state",  # SQLAlchemy internal
        ]
        exclude_fields.extend(default_exclude)

        result = {}
        for column in entity.__table__.columns:
            field_name = column.name
            if field_name not in exclude_fields:
                value = getattr(entity, field_name, None)

                # Convert UUIDs and datetimes to strings for JSON serialization
                if isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                elif hasattr(value, "__dict__"):  # Enum
                    value = value.value if hasattr(value, "value") else str(value)

                result[field_name] = value

        return result
