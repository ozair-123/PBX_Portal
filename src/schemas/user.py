"""User schemas for API request/response validation."""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    
    tenant_id: UUID = Field(..., description="Tenant ID")
    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Email address (unique)")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    role: str = Field(default="end_user", description="User role (platform_admin, tenant_admin, support, end_user)")
    
    # Optional fields
    outbound_callerid: Optional[str] = Field(None, max_length=20, description="Outbound caller ID (E.164 format)")
    voicemail_enabled: bool = Field(default=True, description="Enable voicemail")
    voicemail_pin: Optional[str] = Field(None, min_length=4, max_length=10, description="Voicemail PIN")
    dnd_enabled: bool = Field(default=False, description="Do Not Disturb enabled")
    call_forward_destination: Optional[str] = Field(None, max_length=255, description="Call forwarding destination")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed_roles = ['platform_admin', 'tenant_admin', 'support', 'end_user']
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v
    
    @field_validator('voicemail_pin')
    @classmethod
    def validate_pin(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.isdigit():
            raise ValueError("Voicemail PIN must contain only digits")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "password": "SecurePassword123!",
                "role": "end_user",
                "voicemail_enabled": True,
                "voicemail_pin": "1234"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[str] = None
    status: Optional[str] = Field(None, description="User status (active, suspended, deleted)")
    
    outbound_callerid: Optional[str] = Field(None, max_length=20)
    voicemail_enabled: Optional[bool] = None
    voicemail_pin: Optional[str] = Field(None, min_length=4, max_length=10)
    dnd_enabled: Optional[bool] = None
    call_forward_destination: Optional[str] = Field(None, max_length=255)
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed_roles = ['platform_admin', 'tenant_admin', 'support', 'end_user']
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed_statuses = ['active', 'suspended', 'deleted']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v
    
    @field_validator('voicemail_pin')
    @classmethod
    def validate_pin(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.isdigit():
            raise ValueError("Voicemail PIN must contain only digits")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe Updated",
                "dnd_enabled": True
            }
        }


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive fields)."""
    
    id: UUID
    tenant_id: UUID
    name: str
    email: str
    role: str
    status: str
    extension: int
    
    outbound_callerid: Optional[str]
    voicemail_enabled: bool
    dnd_enabled: bool
    call_forward_destination: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "role": "end_user",
                "status": "active",
                "extension": 1000,
                "outbound_callerid": "+15551234567",
                "voicemail_enabled": True,
                "dnd_enabled": False,
                "call_forward_destination": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "role": "end_user",
                        "status": "active",
                        "extension": 1000,
                        "voicemail_enabled": True,
                        "dnd_enabled": False,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10
            }
        }
