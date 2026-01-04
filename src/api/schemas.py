"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, UUID4


# ============================================================================
# User Story 1: Create User with Extension Allocation
# ============================================================================

class CreateUserRequest(BaseModel):
    """Request body for creating a new user."""

    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address (must be unique)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "John Doe",
                    "email": "john.doe@example.com"
                }
            ]
        }
    }


class ExtensionResponse(BaseModel):
    """Extension details in API responses."""

    id: str = Field(..., description="Extension UUID")
    number: int = Field(..., ge=1000, le=1999, description="Extension number (1000-1999)")
    secret: str = Field(..., description="SIP authentication secret")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "number": 1042,
                    "secret": "a8K3mP9xQ2vR7wN5",
                    "created_at": "2024-01-15T10:30:00"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """Response body for user operations."""

    id: str = Field(..., description="User UUID")
    tenant_id: str = Field(..., description="Tenant UUID")
    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email address")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    extension: Optional[ExtensionResponse] = Field(None, description="Assigned extension details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "tenant_id": "a0000000-0000-0000-0000-000000000000",
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "created_at": "2024-01-15T10:30:00",
                    "extension": {
                        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                        "number": 1042,
                        "secret": "a8K3mP9xQ2vR7wN5",
                        "created_at": "2024-01-15T10:30:00"
                    }
                }
            ]
        }
    }


# ============================================================================
# User Story 2: Apply Configuration to Asterisk
# ============================================================================

class ApplyRequest(BaseModel):
    """Request body for applying configuration."""

    triggered_by: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Username or identifier of who triggered the apply"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "triggered_by": "admin@example.com"
                }
            ]
        }
    }


class ApplyResponse(BaseModel):
    """Response body for successful apply operation."""

    message: str = Field(..., description="Success message")
    audit_log_id: str = Field(..., description="UUID of the audit log entry")
    files_written: List[str] = Field(..., description="List of configuration files written")
    reload_results: dict = Field(..., description="Results from Asterisk reload commands")
    users_applied: int = Field(..., description="Number of users processed")
    extensions_generated: int = Field(..., description="Number of extensions generated")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Configuration applied successfully",
                    "audit_log_id": "9b7d8c6e-5f4a-3b2c-1d0e-9f8a7b6c5d4e",
                    "files_written": [
                        "/etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf",
                        "/etc/asterisk/extensions.d/synergycall/generated_routing.conf"
                    ],
                    "reload_results": {
                        "pjsip": {"exit_code": 0, "stdout": "PJSIP reloaded", "stderr": ""},
                        "dialplan": {"exit_code": 0, "stdout": "Dialplan reloaded", "stderr": ""}
                    },
                    "users_applied": 42,
                    "extensions_generated": 42
                }
            ]
        }
    }


class ApplyErrorResponse(BaseModel):
    """Response body for failed apply operation."""

    error: str = Field(..., description="Error message")
    audit_log_id: Optional[str] = Field(None, description="UUID of the audit log entry (if created)")
    details: Optional[dict] = Field(None, description="Additional error details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "Failed to reload Asterisk PJSIP module",
                    "audit_log_id": "9b7d8c6e-5f4a-3b2c-1d0e-9f8a7b6c5d4e",
                    "details": {
                        "pjsip_reload_exit_code": 1,
                        "pjsip_reload_stderr": "Module res_pjsip.so not found"
                    }
                }
            ]
        }
    }


class ApplyAuditLogResponse(BaseModel):
    """Response body for a single apply audit log entry."""

    id: str = Field(..., description="Audit log UUID")
    triggered_at: str = Field(..., description="Timestamp when apply was triggered (ISO 8601)")
    triggered_by: str = Field(..., description="Username or identifier who triggered the apply")
    outcome: str = Field(..., description="Apply outcome: 'success' or 'failure'")
    error_details: Optional[str] = Field(None, description="Error details if outcome was 'failure'")
    files_written: Optional[List[str]] = Field(None, description="List of files written")
    reload_results: Optional[dict] = Field(None, description="Asterisk reload command results")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "9b7d8c6e-5f4a-3b2c-1d0e-9f8a7b6c5d4e",
                    "triggered_at": "2024-01-15T10:30:00",
                    "triggered_by": "admin@example.com",
                    "outcome": "success",
                    "error_details": None,
                    "files_written": [
                        "/etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf",
                        "/etc/asterisk/extensions.d/synergycall/generated_routing.conf"
                    ],
                    "reload_results": {
                        "pjsip": {"success": True},
                        "dialplan": {"success": True}
                    }
                }
            ]
        }
    }


# ============================================================================
# User Story 3: List Users
# ============================================================================

class ListUsersResponse(BaseModel):
    """Response body for listing all users."""

    users: List[UserResponse] = Field(..., description="List of all users with their extensions")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "users": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "tenant_id": "a0000000-0000-0000-0000-000000000000",
                            "name": "John Doe",
                            "email": "john.doe@example.com",
                            "created_at": "2024-01-15T10:30:00",
                            "extension": {
                                "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                                "number": 1042,
                                "secret": "a8K3mP9xQ2vR7wN5",
                                "created_at": "2024-01-15T10:30:00"
                            }
                        }
                    ]
                }
            ]
        }
    }


# ============================================================================
# User Story 4: Delete User
# ============================================================================

class DeleteUserResponse(BaseModel):
    """Response body for user deletion."""

    message: str = Field(..., description="Success message")
    deleted_user_id: str = Field(..., description="UUID of the deleted user")
    freed_extension: Optional[int] = Field(
        None,
        description="Extension number that was freed (1000-1999)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "User deleted successfully",
                    "deleted_user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "freed_extension": 1042
                }
            ]
        }
    }


# ============================================================================
# Common Error Responses
# ============================================================================

class ErrorResponse(BaseModel):
    """Generic error response."""

    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "Validation failed",
                    "details": "Email 'invalid-email' is not a valid email address"
                }
            ]
        }
    }
