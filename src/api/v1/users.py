"""User management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from ...database import get_db
from ...auth.rbac import require_role, get_current_user
from ...schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from ...services.user_service import UserService

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("tenant_admin")),
):
    """
    Create a new user with automatic extension assignment.
    
    Requires: tenant_admin or platform_admin role
    
    - Automatically assigns next available extension
    - Hashes password before storage
    - Creates audit log entry
    """
    try:
        # Extract request metadata
        source_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Create user via service layer
        user = UserService.create_user(
            session=db,
            tenant_id=user_data.tenant_id,
            name=user_data.name,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
            actor_id=UUID(current_user["user_id"]),
            source_ip=source_ip,
            user_agent=user_agent,
            outbound_callerid=user_data.outbound_callerid,
            voicemail_enabled=user_data.voicemail_enabled,
            voicemail_pin=user_data.voicemail_pin,
            dnd_enabled=user_data.dnd_enabled,
            call_forward_destination=user_data.call_forward_destination,
        )
        
        db.commit()
        db.refresh(user)
        
        return user
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get user by ID.
    
    Requires: authentication
    - Platform admins can view all users
    - Tenant admins can view users in their tenant
    - End users can only view their own profile
    """
    user = UserService.get_user(db, user_id)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Authorization check
    current_user_id = UUID(current_user["user_id"])
    current_user_role = current_user["role"]
    
    if current_user_role == "platform_admin":
        # Platform admins can view all
        pass
    elif current_user_role == "tenant_admin":
        # Tenant admins can view users in their tenant
        if str(user.tenant_id) != current_user.get("tenant_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    else:
        # End users can only view their own profile
        if user.id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return user


@router.get("/", response_model=UserListResponse)
async def list_users(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, suspended, deleted)"),
    role: Optional[str] = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("support")),
):
    """
    List users with filtering and pagination.
    
    Requires: support, tenant_admin, or platform_admin role
    
    - Tenant admins automatically filtered to their tenant
    - Platform admins and support can view all tenants
    """
    # Auto-filter tenant admins to their own tenant
    if current_user["role"] == "tenant_admin" and not tenant_id:
        tenant_id = UUID(current_user["tenant_id"])
    elif current_user["role"] == "tenant_admin" and str(tenant_id) != current_user["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    result = UserService.list_users(
        session=db,
        tenant_id=tenant_id,
        status=status,
        role=role,
        page=page,
        page_size=page_size,
    )
    
    return UserListResponse(**result)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: Request,
    user_updates: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("tenant_admin")),
):
    """
    Update user details.
    
    Requires: tenant_admin or platform_admin role
    
    - Updates only provided fields
    - Passwords are hashed automatically
    - Creates audit log entry
    """
    try:
        # Extract request metadata
        source_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Prepare updates (exclude None values)
        updates = user_updates.model_dump(exclude_unset=True)
        
        # Update user
        user = UserService.update_user(
            session=db,
            user_id=user_id,
            actor_id=UUID(current_user["user_id"]),
            source_ip=source_ip,
            user_agent=user_agent,
            **updates
        )
        
        db.commit()
        db.refresh(user)
        
        return user
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("tenant_admin")),
):
    """
    Soft delete a user (set status to deleted).
    
    Requires: tenant_admin or platform_admin role
    
    - User is soft deleted (status set to 'deleted')
    - Extension is freed for reuse
    - Creates audit log entry
    """
    try:
        # Extract request metadata
        source_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Delete user
        UserService.delete_user(
            session=db,
            user_id=user_id,
            actor_id=UUID(current_user["user_id"]),
            source_ip=source_ip,
            user_agent=user_agent,
        )
        
        db.commit()
        
        return None
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
