"""Tenant model - represents an organization using the PBX system."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from . import Base


class TenantStatus(enum.Enum):
    """Tenant status enum."""
    active = "active"
    suspended = "suspended"


class Tenant(Base):
    """Tenant model.

    Supports multi-tenancy with complete isolation. Each tenant has:
    - Independent users, extensions, DIDs, policies
    - Extension range (ext_min to ext_max)
    - Default inbound destination for unassigned DIDs
    - Default outbound policy for users
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)

    # Extension range management
    ext_min = Column(Integer, nullable=False)
    ext_max = Column(Integer, nullable=False)
    ext_next = Column(Integer, nullable=False)  # Next available extension pointer

    # Default configurations
    default_inbound_destination = Column(String(255), nullable=True)  # e.g., "VOICEMAIL:general", "USER:uuid"
    outbound_policy_id = Column(UUID(as_uuid=True), ForeignKey("outbound_policies.id", ondelete="SET NULL"), nullable=True)

    # Status
    status = Column(SQLEnum(TenantStatus), nullable=False, default=TenantStatus.active)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    phone_numbers = relationship("PhoneNumber", back_populates="tenant")
    # outbound_policy = relationship("OutboundPolicy", foreign_keys=[outbound_policy_id])
    # Note: OutboundPolicy relationship commented out to avoid circular import, will be added in OutboundPolicy model

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', ext_range={self.ext_min}-{self.ext_max})>"

    def has_available_extensions(self) -> bool:
        """Check if tenant has available extensions in the pool."""
        return self.ext_next <= self.ext_max

    def get_next_extension(self) -> int:
        """
        Get next available extension and increment pointer.

        Raises:
            ValueError: If no extensions available
        """
        if not self.has_available_extensions():
            raise ValueError(f"Extension pool exhausted for tenant {self.name}")

        extension = self.ext_next
        self.ext_next += 1
        return extension
