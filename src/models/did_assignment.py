"""DID Assignment model for routing phone numbers to destinations."""
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models import Base


class AssignmentType(enum.Enum):
    """Type of destination for DID assignment."""
    USER = "USER"          # Route to specific user extension
    IVR = "IVR"            # Route to IVR menu
    QUEUE = "QUEUE"        # Route to call queue
    EXTERNAL = "EXTERNAL"  # Route to external dialplan context


class DIDAssignment(Base):
    """Assignment of a phone number to a destination.

    Polymorphic assignment based on assigned_type:
    - USER/IVR/QUEUE: assigned_id references the entity ID, assigned_value is NULL
    - EXTERNAL: assigned_id is NULL, assigned_value contains dialplan context
    """
    __tablename__ = "did_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number_id = Column(
        UUID(as_uuid=True),
        ForeignKey("phone_numbers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    assigned_type = Column(SQLEnum(AssignmentType), nullable=False)
    assigned_id = Column(UUID(as_uuid=True), nullable=True)
    assigned_value = Column(String(255), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    phone_number = relationship("PhoneNumber", back_populates="assignment")
    creator = relationship("User", foreign_keys=[created_by])

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(assigned_type IN ('USER', 'IVR', 'QUEUE') AND assigned_id IS NOT NULL AND assigned_value IS NULL) OR "
            "(assigned_type = 'EXTERNAL' AND assigned_id IS NULL AND assigned_value IS NOT NULL)",
            name="did_assignment_type_consistency"
        ),
    )

    def __repr__(self):
        target = self.assigned_id if self.assigned_id else self.assigned_value
        return f"<DIDAssignment(phone_number_id={self.phone_number_id}, type={self.assigned_type.value}, target={target})>"
