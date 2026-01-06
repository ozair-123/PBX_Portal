"""Pydantic schemas for phone number and DID management."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
import re

from src.models.phone_number import PhoneNumberStatus
from src.models.did_assignment import AssignmentType


# E.164 validation pattern
E164_PATTERN = re.compile(r'^\+[1-9]\d{1,14}$')


class DIDImportItem(BaseModel):
    """Single DID to import."""
    number: str = Field(..., description="Phone number in E.164 format (e.g., +15551234567)")
    provider: Optional[str] = Field(None, max_length=255, description="Provider name (optional)")
    provider_metadata: Optional[dict] = Field(default_factory=dict, description="Provider-specific metadata (optional)")

    @field_validator('number')
    @classmethod
    def validate_e164(cls, v: str) -> str:
        """Validate E.164 format."""
        if not E164_PATTERN.match(v):
            raise ValueError(f"Phone number must be in E.164 format: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "number": "+15551234567",
                "provider": "Twilio",
                "provider_metadata": {"sid": "PN123abc"}
            }
        }


class DIDImportRequest(BaseModel):
    """Request to import multiple DIDs."""
    dids: List[DIDImportItem] = Field(..., max_length=10000, description="List of DIDs to import (max 10,000)")

    @field_validator('dids')
    @classmethod
    def validate_not_empty(cls, v: List[DIDImportItem]) -> List[DIDImportItem]:
        """Ensure at least one DID is provided."""
        if not v:
            raise ValueError("At least one DID must be provided")
        if len(v) > 10000:
            raise ValueError("Maximum 10,000 DIDs can be imported at once")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "dids": [
                    {"number": "+15551234567", "provider": "Twilio"},
                    {"number": "+15551234568", "provider": "Twilio"}
                ]
            }
        }


class DIDImportError(BaseModel):
    """Error details for a failed DID import."""
    number: str = Field(..., description="Phone number that failed")
    error: str = Field(..., description="Error message")


class DIDImportResponse(BaseModel):
    """Response from DID import operation."""
    imported: int = Field(..., description="Number of DIDs successfully imported")
    failed: int = Field(..., description="Number of DIDs that failed")
    errors: List[DIDImportError] = Field(default_factory=list, description="List of errors for failed DIDs")

    class Config:
        json_schema_extra = {
            "example": {
                "imported": 98,
                "failed": 2,
                "errors": [
                    {"number": "+1234", "error": "Invalid E.164 format"},
                    {"number": "+15551234567", "error": "Duplicate number"}
                ]
            }
        }


class DIDAssignmentResponse(BaseModel):
    """DID assignment details."""
    id: UUID
    assigned_type: AssignmentType
    assigned_id: Optional[UUID] = None
    assigned_value: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "assigned_type": "USER",
                "assigned_id": "987e6543-e21b-12d3-a456-426614174000",
                "assigned_value": None,
                "created_by": "111e2222-e33b-12d3-a456-426614174000",
                "created_at": "2026-01-06T12:00:00",
                "updated_at": "2026-01-06T12:00:00"
            }
        }


class PhoneNumberResponse(BaseModel):
    """Phone number with optional assignment."""
    id: UUID
    number: str
    status: PhoneNumberStatus
    tenant_id: Optional[UUID] = None
    provider: Optional[str] = None
    provider_metadata: Optional[dict] = None
    assignment: Optional[DIDAssignmentResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "number": "+15551234567",
                "status": "ASSIGNED",
                "tenant_id": "987e6543-e21b-12d3-a456-426614174000",
                "provider": "Twilio",
                "provider_metadata": {"sid": "PN123abc"},
                "assignment": {
                    "id": "111e2222-e33b-12d3-a456-426614174000",
                    "assigned_type": "USER",
                    "assigned_id": "222e3333-e44b-12d3-a456-426614174000",
                    "assigned_value": None,
                    "created_by": "333e4444-e55b-12d3-a456-426614174000",
                    "created_at": "2026-01-06T12:00:00",
                    "updated_at": "2026-01-06T12:00:00"
                },
                "created_at": "2026-01-06T12:00:00",
                "updated_at": "2026-01-06T12:00:00"
            }
        }


class PhoneNumberListResponse(BaseModel):
    """Paginated list of phone numbers."""
    items: List[PhoneNumberResponse]
    total: int = Field(..., description="Total number of phone numbers")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=1000, description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "number": "+15551234567",
                        "status": "ASSIGNED",
                        "tenant_id": "987e6543-e21b-12d3-a456-426614174000",
                        "provider": "Twilio",
                        "provider_metadata": {},
                        "assignment": None,
                        "created_at": "2026-01-06T12:00:00",
                        "updated_at": "2026-01-06T12:00:00"
                    }
                ],
                "total": 100,
                "page": 1,
                "page_size": 50,
                "pages": 2
            }
        }


class DIDAllocateRequest(BaseModel):
    """Request to allocate DIDs to a tenant."""
    tenant_id: UUID = Field(..., description="Tenant ID to allocate DIDs to")

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "987e6543-e21b-12d3-a456-426614174000"
            }
        }


class DIDAssignRequest(BaseModel):
    """Request to assign a DID to a destination."""
    assigned_type: AssignmentType = Field(..., description="Type of destination (USER, IVR, QUEUE, EXTERNAL)")
    assigned_id: Optional[UUID] = Field(None, description="ID of destination entity (for USER, IVR, QUEUE)")
    assigned_value: Optional[str] = Field(None, max_length=255, description="Dialplan context (for EXTERNAL)")

    @field_validator('assigned_id', 'assigned_value')
    @classmethod
    def validate_polymorphic_fields(cls, v, info):
        """Validate polymorphic assignment fields."""
        assigned_type = info.data.get('assigned_type')
        field_name = info.field_name

        if assigned_type in [AssignmentType.USER, AssignmentType.IVR, AssignmentType.QUEUE]:
            if field_name == 'assigned_id' and v is None:
                raise ValueError(f"assigned_id is required for {assigned_type.value}")
            if field_name == 'assigned_value' and v is not None:
                raise ValueError(f"assigned_value must be null for {assigned_type.value}")

        elif assigned_type == AssignmentType.EXTERNAL:
            if field_name == 'assigned_value' and not v:
                raise ValueError("assigned_value is required for EXTERNAL")
            if field_name == 'assigned_id' and v is not None:
                raise ValueError("assigned_id must be null for EXTERNAL")

        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "assigned_type": "USER",
                    "assigned_id": "222e3333-e44b-12d3-a456-426614174000",
                    "assigned_value": None
                },
                {
                    "assigned_type": "EXTERNAL",
                    "assigned_id": None,
                    "assigned_value": "custom-ivr-context"
                }
            ]
        }
