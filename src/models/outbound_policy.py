"""OutboundPolicy model for managing outbound call policies."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from . import Base


class OutboundPolicy(Base):
    """Outbound policy model for call routing rules."""
    __tablename__ = "outbound_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<OutboundPolicy(id={self.id}, name={self.name})>"
