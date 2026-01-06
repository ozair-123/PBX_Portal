"""
AuditLog model - immutable log of all system changes.

Provides complete audit trail for compliance, troubleshooting, and rollback.
"""

from datetime import datetime
from uuid import uuid4
import enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from . import Base


class AuditAction(enum.Enum):
    """Audit action enum."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    APPLY = "APPLY"


class AuditLog(Base):
    """
    Audit log model for tracking all system changes.

    This is an immutable append-only log. Once created, audit entries
    are never updated or deleted (except for compliance-mandated purges).

    Captures:
    - Who made the change (actor_id)
    - What action was performed (action)
    - What entity was affected (entity_type, entity_id)
    - Complete before/after state (before_json, after_json)
    - When it happened (timestamp)
    - Where it came from (source_ip, user_agent)
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Action details
    action = Column(SQLEnum(AuditAction), nullable=False)
    entity_type = Column(String(50), nullable=False)  # e.g., "User", "Device", "DID", "Trunk"
    entity_id = Column(UUID(as_uuid=True), nullable=False)  # ID of the affected entity

    # State tracking (enables rollback and review)
    before_json = Column(JSONB, nullable=True)  # State before change (NULL for CREATE)
    after_json = Column(JSONB, nullable=True)  # State after change (NULL for DELETE)

    # Metadata
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    source_ip = Column(String(45), nullable=True)  # IPv4 (15) or IPv6 (45) address
    user_agent = Column(Text, nullable=True)  # Browser/client user agent string

    # Relationships
    tenant = relationship("Tenant")
    actor = relationship("User")

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, action={self.action.value}, "
            f"entity_type='{self.entity_type}', entity_id={self.entity_id}, "
            f"timestamp={self.timestamp})>"
        )

    def get_changed_fields(self) -> dict:
        """
        Get fields that changed between before and after states.

        Returns:
            Dictionary of field names to (before, after) tuples

        Example:
            >>> log = AuditLog(
            ...     before_json={"status": "active", "name": "John"},
            ...     after_json={"status": "suspended", "name": "John"}
            ... )
            >>> log.get_changed_fields()
            {'status': ('active', 'suspended')}
        """
        if not self.before_json or not self.after_json:
            return {}

        changes = {}
        all_keys = set(self.before_json.keys()) | set(self.after_json.keys())

        for key in all_keys:
            before_val = self.before_json.get(key)
            after_val = self.after_json.get(key)

            if before_val != after_val:
                changes[key] = (before_val, after_val)

        return changes
