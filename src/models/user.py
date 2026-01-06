"""User model - represents a person who can use the PBX."""

from datetime import datetime
from uuid import uuid4
import enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class UserRole(enum.Enum):
    """User role enum for RBAC."""
    platform_admin = "platform_admin"  # Full system access
    tenant_admin = "tenant_admin"  # Manage own tenant
    support = "support"  # Read-only troubleshooting
    end_user = "end_user"  # Self-service only


class UserStatus(enum.Enum):
    """User status enum."""
    active = "active"
    suspended = "suspended"
    deleted = "deleted"  # Soft delete


class User(Base):
    """User model.

    Each user:
    - Belongs to exactly one tenant
    - Has exactly one auto-assigned extension
    - Can have multiple devices (desk phone, softphone, mobile)
    - Has authentication credentials (password_hash)
    - Has role-based permissions (role)
    - Can configure self-service settings (DND, call forwarding, voicemail)
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Identity
    name = Column(String(255), nullable=False)  # Full name (display)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)  # Argon2/bcrypt hash

    # Authorization
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.end_user)
    status = Column(SQLEnum(UserStatus), nullable=False, default=UserStatus.active)

    # Extension (auto-assigned, unique per tenant)
    extension = Column(Integer, nullable=False)

    # Outbound calling
    outbound_callerid = Column(String(20), nullable=True)  # E.164 format (e.g., "+15551234567")

    # Voicemail configuration
    voicemail_enabled = Column(Boolean, nullable=False, default=True)
    voicemail_pin_hash = Column(Text, nullable=True)  # Bcrypt hash of PIN

    # Self-service settings (end user can modify these)
    dnd_enabled = Column(Boolean, nullable=False, default=False)  # Do Not Disturb
    call_forward_destination = Column(String(255), nullable=True)  # Extension or E.164 number

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    # extension relationship removed - extension is now a direct column (simpler design)
    # devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', extension={self.extension}, role={self.role.value})>"

    def is_admin(self) -> bool:
        """Check if user has admin privileges (platform_admin or tenant_admin)."""
        return self.role in (UserRole.platform_admin, UserRole.tenant_admin)

    def can_access_tenant(self, tenant_id: str) -> bool:
        """Check if user can access resources in given tenant."""
        # Platform admins can access all tenants
        if self.role == UserRole.platform_admin:
            return True
        # Other users can only access their own tenant
        return str(self.tenant_id) == str(tenant_id)

    def is_active(self) -> bool:
        """Check if user is active (not suspended or deleted)."""
        return self.status == UserStatus.active
