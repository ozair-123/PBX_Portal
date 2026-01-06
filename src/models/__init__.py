"""Database models for PBX Control Portal."""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .tenant import Tenant
from .user import User
from .audit_log import AuditLog
from .apply_audit_log import ApplyJob, ApplyAuditLog  # ApplyAuditLog is alias for backward compat
from .phone_number import PhoneNumber, PhoneNumberStatus
from .did_assignment import DIDAssignment, AssignmentType

__all__ = [
    "Base",
    "Tenant",
    "User",
    "AuditLog",
    "ApplyJob",
    "ApplyAuditLog",
    "PhoneNumber",
    "PhoneNumberStatus",
    "DIDAssignment",
    "AssignmentType",
]
