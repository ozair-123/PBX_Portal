"""Phone Number model for DID management."""
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Enum as SQLEnum,
    ForeignKey,
    CheckConstraint,
    Index,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.models import Base


class PhoneNumberStatus(enum.Enum):
    """Status of a phone number in the DID lifecycle."""
    UNASSIGNED = "UNASSIGNED"  # In global pool, no tenant
    ALLOCATED = "ALLOCATED"    # Assigned to tenant, not to destination
    ASSIGNED = "ASSIGNED"      # Assigned to tenant and destination


class PhoneNumber(Base):
    """Phone number (DID) for inbound call routing.

    Lifecycle:
    - UNASSIGNED: In global pool, available for allocation
    - ALLOCATED: Assigned to tenant, available for assignment to destination
    - ASSIGNED: Assigned to tenant and destination (user, IVR, queue, external)
    """
    __tablename__ = "phone_numbers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number = Column(String(16), nullable=False, unique=True, index=True)
    status = Column(
        SQLEnum(PhoneNumberStatus),
        nullable=False,
        default=PhoneNumberStatus.UNASSIGNED,
        index=True
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    provider = Column(String(255), nullable=True)
    provider_metadata = Column(JSONB, nullable=True, default={})
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="phone_numbers")
    assignment = relationship(
        "DIDAssignment",
        back_populates="phone_number",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "number ~ '^\\+[1-9]\\d{1,14}$'",
            name="phone_number_e164_format"
        ),
        CheckConstraint(
            "(status = 'UNASSIGNED' AND tenant_id IS NULL) OR "
            "(status IN ('ALLOCATED', 'ASSIGNED') AND tenant_id IS NOT NULL)",
            name="phone_number_tenant_consistency"
        ),
        Index("idx_phone_numbers_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self):
        return f"<PhoneNumber(id={self.id}, number={self.number}, status={self.status.value})>"
