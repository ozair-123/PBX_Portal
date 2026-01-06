"""
ApplyJob model - represents one configuration apply operation.

Provides audit trail and rollback capability for apply operations.
"""

from datetime import datetime
from uuid import uuid4
import enum

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from . import Base


class ApplyStatus(enum.Enum):
    """Apply operation status enum."""
    PENDING = "PENDING"  # Apply created, not yet started
    RUNNING = "RUNNING"  # Apply in progress
    SUCCESS = "SUCCESS"  # Apply completed successfully
    FAILED = "FAILED"  # Apply failed (without rollback)
    ROLLED_BACK = "ROLLED_BACK"  # Apply failed and was rolled back


class ApplyJob(Base):
    """
    Apply job model for configuration apply operations.

    Each apply operation:
    - Validates pending changes for conflicts
    - Generates Asterisk configuration files
    - Backs up current working config
    - Writes new config files atomically
    - Reloads Asterisk modules
    - Automatically rolls back on failure
    - Records complete audit trail

    Status lifecycle:
    PENDING → RUNNING → SUCCESS
    PENDING → RUNNING → FAILED (if rollback not attempted)
    PENDING → RUNNING → ROLLED_BACK (if rollback executed)
    """
    __tablename__ = "apply_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)

    # Status tracking
    status = Column(SQLEnum(ApplyStatus), nullable=False, default=ApplyStatus.PENDING)

    # Timing
    started_at = Column(DateTime, nullable=True)  # When apply started (status → RUNNING)
    ended_at = Column(DateTime, nullable=True)  # When apply completed (SUCCESS/FAILED/ROLLED_BACK)

    # Error handling
    error_text = Column(Text, nullable=True)  # Error message if FAILED or ROLLED_BACK

    # Change summary
    diff_summary = Column(Text, nullable=True)  # Human-readable summary (e.g., "Added 3 users, updated 2 DIDs")

    # Rollback data
    config_files_json = Column(JSONB, nullable=True)  # List of config files written (for rollback)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant")
    actor = relationship("User")

    def __repr__(self):
        return (
            f"<ApplyJob(id={self.id}, status={self.status.value}, "
            f"tenant_id={self.tenant_id}, created_at={self.created_at})>"
        )

    def start(self):
        """Mark apply as started."""
        self.status = ApplyStatus.RUNNING
        self.started_at = datetime.utcnow()

    def succeed(self, diff_summary: str = None):
        """Mark apply as successful."""
        self.status = ApplyStatus.SUCCESS
        self.ended_at = datetime.utcnow()
        self.diff_summary = diff_summary

    def fail(self, error_text: str):
        """Mark apply as failed (without rollback)."""
        self.status = ApplyStatus.FAILED
        self.ended_at = datetime.utcnow()
        self.error_text = error_text

    def rollback(self, error_text: str):
        """Mark apply as rolled back."""
        self.status = ApplyStatus.ROLLED_BACK
        self.ended_at = datetime.utcnow()
        self.error_text = error_text

    def get_duration_seconds(self) -> float:
        """
        Get apply operation duration in seconds.

        Returns:
            Duration in seconds, or 0 if not yet started/ended
        """
        if not self.started_at or not self.ended_at:
            return 0.0

        delta = self.ended_at - self.started_at
        return delta.total_seconds()


# Alias for backward compatibility with existing code
ApplyAuditLog = ApplyJob
