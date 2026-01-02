"""ApplyAuditLog model - records each Apply action for troubleshooting and compliance."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, CheckConstraint, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB

from . import Base


class ApplyAuditLog(Base):
    """ApplyAuditLog model.

    Records each Apply action with outcome, files written, and reload results.
    """
    __tablename__ = "apply_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    triggered_by = Column(String(255), nullable=False)
    outcome = Column(String(50), nullable=False)
    error_details = Column(Text, nullable=True)
    files_written = Column(ARRAY(Text), nullable=True)
    reload_results = Column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint("outcome IN ('success', 'failure')", name="outcome_check"),
    )

    def __repr__(self):
        return f"<ApplyAuditLog(id={self.id}, outcome='{self.outcome}')>"
