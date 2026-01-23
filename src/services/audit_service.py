"""Audit logging service for tracking user actions."""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from ..models.audit_log import AuditLog


class AuditService:
    """Service for creating audit log entries."""

    @staticmethod
    def entity_to_dict(entity, exclude_fields: list = None) -> dict:
        """
        Convert a SQLAlchemy entity to a dictionary.

        Args:
            entity: SQLAlchemy model instance
            exclude_fields: List of field names to exclude from output

        Returns:
            Dictionary representation of the entity
        """
        if entity is None:
            return None

        exclude_fields = exclude_fields or []
        result = {}
        for column in entity.__table__.columns:
            if column.name in exclude_fields:
                continue
            value = getattr(entity, column.name)
            # Convert UUIDs and datetime objects to strings
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, type(None))):
                value = str(value)
            result[column.name] = value
        return result

    @staticmethod
    def log_create(
        session: Session,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        after_state: dict = None,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a resource creation event.

        Args:
            session: Database session
            actor_id: User ID performing the action
            entity_type: Type of resource created
            entity_id: ID of created resource
            after_state: State after creation
            tenant_id: Optional tenant ID
            source_ip: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry
        """
        audit = AuditLog(
            actor_id=actor_id,
            tenant_id=tenant_id,
            action="CREATE",
            entity_type=entity_type,
            entity_id=entity_id,
            after_json=after_state,
            source_ip=source_ip,
            user_agent=user_agent,
        )
        session.add(audit)
        return audit

    @staticmethod
    def log_update(
        session: Session,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        before_state: dict = None,
        after_state: dict = None,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a resource update event.

        Args:
            session: Database session
            actor_id: User ID performing the action
            entity_type: Type of resource updated
            entity_id: ID of updated resource
            before_state: State before update
            after_state: State after update
            tenant_id: Optional tenant ID
            source_ip: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry
        """
        audit = AuditLog(
            actor_id=actor_id,
            tenant_id=tenant_id,
            action="UPDATE",
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before_state,
            after_json=after_state,
            source_ip=source_ip,
            user_agent=user_agent,
        )
        session.add(audit)
        return audit

    @staticmethod
    def log_delete(
        session: Session,
        actor_id: UUID,
        entity_type: str,
        entity_id: UUID,
        before_state: dict = None,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a resource deletion event.

        Args:
            session: Database session
            actor_id: User ID performing the action
            entity_type: Type of resource deleted
            entity_id: ID of deleted resource
            before_state: State before deletion
            tenant_id: Optional tenant ID
            source_ip: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry
        """
        audit = AuditLog(
            actor_id=actor_id,
            tenant_id=tenant_id,
            action="DELETE",
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before_state,
            source_ip=source_ip,
            user_agent=user_agent,
        )
        session.add(audit)
        return audit

    @staticmethod
    def log_login(
        session: Session,
        actor_id: UUID,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a user login event.

        Args:
            session: Database session
            actor_id: User ID performing the login
            tenant_id: Optional tenant ID
            source_ip: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry
        """
        audit = AuditLog(
            actor_id=actor_id,
            tenant_id=tenant_id,
            action="LOGIN",
            entity_type="auth",
            entity_id=actor_id,
            source_ip=source_ip,
            user_agent=user_agent,
        )
        session.add(audit)
        return audit

    @staticmethod
    def log_logout(
        session: Session,
        actor_id: UUID,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a user logout event.

        Args:
            session: Database session
            actor_id: User ID performing the logout
            tenant_id: Optional tenant ID
            source_ip: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry
        """
        audit = AuditLog(
            actor_id=actor_id,
            tenant_id=tenant_id,
            action="LOGOUT",
            entity_type="auth",
            entity_id=actor_id,
            source_ip=source_ip,
            user_agent=user_agent,
        )
        session.add(audit)
        return audit

    @staticmethod
    def log_action(
        session: Session,
        actor_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[UUID] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a generic user action.

        Args:
            session: Database session
            actor_id: User ID performing the action
            action: Action name (e.g., "create", "update", "delete")
            entity_type: Type of resource affected
            entity_id: ID of resource affected
            tenant_id: Optional tenant ID
            before_state: State before action
            after_state: State after action
            source_ip: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry
        """
        audit = AuditLog(
            actor_id=actor_id,
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before_state,
            after_json=after_state,
            source_ip=source_ip,
            user_agent=user_agent,
        )
        session.add(audit)
        return audit
