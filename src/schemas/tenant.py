"""Tenant schemas for API request/response validation."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Tenant name (unique)")
    ext_min: int = Field(..., ge=1000, le=99999, description="Minimum extension number")
    ext_max: int = Field(..., ge=1000, le=99999, description="Maximum extension number")
    
    default_inbound_destination: Optional[str] = Field(None, max_length=255, description="Default inbound destination")
    
    @field_validator('ext_max')
    @classmethod
    def validate_extension_range(cls, v: int, info) -> int:
        ext_min = info.data.get('ext_min')
        if ext_min and v <= ext_min:
            raise ValueError("ext_max must be greater than ext_min")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation",
                "ext_min": 1000,
                "ext_max": 1999
            }
        }


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    ext_min: Optional[int] = Field(None, ge=1000, le=99999)
    ext_max: Optional[int] = Field(None, ge=1000, le=99999)
    status: Optional[str] = Field(None, description="Tenant status (active, suspended)")
    default_inbound_destination: Optional[str] = Field(None, max_length=255)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed_statuses = ['active', 'suspended']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation Updated",
                "status": "active"
            }
        }


class TenantResponse(BaseModel):
    """Schema for tenant response."""
    
    id: UUID
    name: str
    ext_min: int
    ext_max: int
    ext_next: int
    status: str
    default_inbound_destination: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Acme Corporation",
                "ext_min": 1000,
                "ext_max": 1999,
                "ext_next": 1000,
                "status": "active",
                "default_inbound_destination": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class TenantListResponse(BaseModel):
    """Schema for paginated tenant list response."""
    
    tenants: List[TenantResponse]
    total: int
    page: int
    page_size: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenants": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Acme Corporation",
                        "ext_min": 1000,
                        "ext_max": 1999,
                        "ext_next": 1000,
                        "status": "active",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10
            }
        }
