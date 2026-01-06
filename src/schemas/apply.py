"""Apply job schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ApplyRequest(BaseModel):
    """Schema for triggering an apply operation."""
    
    tenant_id: Optional[UUID] = Field(None, description="Apply for specific tenant only (optional)")
    force: bool = Field(default=False, description="Force apply even if validation fails")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": None,
                "force": False
            }
        }


class ValidationResponse(BaseModel):
    """Schema for configuration validation response."""
    
    valid: bool
    errors: List[str]
    warnings: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "errors": [],
                "warnings": ["Tenant XYZ is near extension pool exhaustion"]
            }
        }


class ApplyJobResponse(BaseModel):
    """Schema for apply job response."""
    
    id: UUID
    tenant_id: Optional[UUID]
    actor_id: UUID
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    error_text: Optional[str]
    diff_summary: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": None,
                "actor_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "SUCCESS",
                "started_at": "2024-01-01T00:00:00Z",
                "ended_at": "2024-01-01T00:00:05Z",
                "error_text": None,
                "diff_summary": "Applied 10 users, 2 tenants",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class ApplyJobListResponse(BaseModel):
    """Schema for paginated apply job list."""
    
    jobs: List[ApplyJobResponse]
    total: int
    page: int
    page_size: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [],
                "total": 10,
                "page": 1,
                "page_size": 10
            }
        }
