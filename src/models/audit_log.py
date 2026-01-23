"""
AuditLog model - general purpose audit trail for API operations.

Tracks user actions and changes across the system.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from . import Base


class AuditLog(Base):
    """
    General audit log for tracking user actions.

    Records all significant API operations for compliance and debugging.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Who
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)

    # What
    action = Column(String(50), nullable=False)  # e.g., "create", "update", "delete"
    entity_type = Column(String(50), nullable=False)  # e.g., "user", "tenant", "phone_number"
    entity_id = Column(UUID(as_uuid=True), nullable=False)  # ID of affected resource

    # Details
    before_json = Column(JSONB, nullable=True)  # State before change
    after_json = Column(JSONB, nullable=True)   # State after change

    # Context
    source_ip = Column(String(45), nullable=True)  # Client IP address
    user_agent = Column(Text, nullable=True)  # Client user agent string

    # When
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    actor = relationship("User", foreign_keys=[actor_id])
    tenant = relationship("Tenant")

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"entity_type={self.entity_type}, timestamp={self.timestamp})>"
        )
