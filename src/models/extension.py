"""Extension model - represents a SIP extension number allocated to a user."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class Extension(Base):
    """Extension model.

    Extension numbers: 1000-1999 (1000 total).
    UNIQUE constraint on number prevents race conditions during allocation.
    """
    __tablename__ = "extensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    number = Column(Integer, nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    secret = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="extension")

    __table_args__ = (
        CheckConstraint("number >= 1000 AND number <= 1999", name="extension_number_range"),
    )

    def __repr__(self):
        return f"<Extension(number={self.number}, user_id={self.user_id})>"
