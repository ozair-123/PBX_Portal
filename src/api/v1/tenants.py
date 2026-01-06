"""Tenant management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from ...database import get_db
from ...auth.rbac import require_role, get_current_user
from ...schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantListResponse
from ...services.tenant_service import TenantService

router = APIRouter()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: Request,
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("platform_admin")),
):
    """
    Create a new tenant with extension range.
    
    Requires: platform_admin role only
    
    - Sets up extension range (ext_min to ext_max)
    - Initializes ext_next to ext_min
    - Creates audit log entry
    """
    try:
        # Extract request metadata
        source_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Create tenant via service layer
        tenant = TenantService.create_tenant(
            session=db,
            name=tenant_data.name,
            ext_min=tenant_data.ext_min,
            ext_max=tenant_data.ext_max,
            actor_id=UUID(current_user["user_id"]),
            source_ip=source_ip,
            user_agent=user_agent,
            default_inbound_destination=tenant_data.default_inbound_destination,
        )
        
        db.commit()
        db.refresh(tenant)
        
        return tenant
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("support")),
):
    """
    Get tenant by ID.
    
    Requires: support, tenant_admin, or platform_admin role
    
    - Tenant admins can only view their own tenant
    - Platform admins and support can view all tenants
    """
    tenant = TenantService.get_tenant(db, tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    # Authorization check for tenant admins
    if current_user["role"] == "tenant_admin":
        if str(tenant.id) != current_user.get("tenant_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return tenant


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    status: Optional[str] = Query(None, description="Filter by status (active, suspended)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("support")),
):
    """
    List tenants with filtering and pagination.
    
    Requires: support or platform_admin role
    
    - Returns all tenants visible to the user
    - Supports pagination and status filtering
    """
    result = TenantService.list_tenants(
        session=db,
        status=status,
        page=page,
        page_size=page_size,
    )
    
    return TenantListResponse(**result)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    request: Request,
    tenant_updates: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("platform_admin")),
):
    """
    Update tenant details.
    
    Requires: platform_admin role only
    
    - Updates only provided fields
    - Validates extension range changes
    - Creates audit log entry
    """
    try:
        # Extract request metadata
        source_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Prepare updates (exclude None values)
        updates = tenant_updates.model_dump(exclude_unset=True)
        
        # Update tenant
        tenant = TenantService.update_tenant(
            session=db,
            tenant_id=tenant_id,
            actor_id=UUID(current_user["user_id"]),
            source_ip=source_ip,
            user_agent=user_agent,
            **updates
        )
        
        db.commit()
        db.refresh(tenant)
        
        return tenant
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
