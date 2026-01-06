"""Apply configuration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from ...database import get_db
from ...auth.rbac import require_role, get_current_user
from ...schemas.apply import (
    ApplyRequest,
    ValidationResponse,
    ApplyJobResponse,
    ApplyJobListResponse,
)
from ...services.apply_service import ApplyService
from ...services.apply_service_enhanced import EnhancedApplyService

router = APIRouter()


@router.post("/validate", response_model=ValidationResponse)
async def validate_configuration(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("tenant_admin")),
):
    """
    Validate current configuration without applying.
    
    Requires: tenant_admin or platform_admin role
    
    Checks:
    - Extension uniqueness within tenants
    - No duplicate emails
    - All users have assigned extensions
    - Tenant extension ranges are valid
    """
    try:
        validation = ApplyService.validate_configuration(db)
        return ValidationResponse(**validation)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/", response_model=ApplyJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def apply_configuration(
    request: Request,
    apply_request: ApplyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("tenant_admin")),
):
    """
    Apply current configuration to Asterisk.
    
    Requires: tenant_admin or platform_admin role
    
    Workflow:
    1. Acquire advisory lock (prevents concurrent applies)
    2. Validate configuration
    3. Backup current configs
    4. Generate new dialplan
    5. Write configs atomically
    6. Reload Asterisk via AMI
    7. Rollback on failure
    8. Release lock
    
    Returns 202 Accepted with apply job ID for status tracking.
    """
    try:
        # Tenant admins can only apply for their own tenant
        tenant_id = apply_request.tenant_id
        if current_user["role"] == "tenant_admin":
            if tenant_id and str(tenant_id) != current_user.get("tenant_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant admins can only apply for their own tenant"
                )
            # Force tenant_id to current user's tenant
            tenant_id = UUID(current_user["tenant_id"]) if current_user.get("tenant_id") else None
        
        # Start apply operation
        apply_job = EnhancedApplyService.apply_configuration_safe(
            session=db,
            actor_id=UUID(current_user["user_id"]),
            tenant_id=tenant_id,
            force=apply_request.force,
        )
        
        return apply_job
        
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Apply failed: {str(e)}"
        )


@router.get("/{job_id}", response_model=ApplyJobResponse)
async def get_apply_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("support")),
):
    """
    Get apply job status by ID.
    
    Requires: support, tenant_admin, or platform_admin role
    
    - Tenant admins can only view jobs for their tenant
    - Platform admins and support can view all jobs
    """
    job = EnhancedApplyService.get_apply_job(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apply job not found"
        )
    
    # Authorization check for tenant admins
    if current_user["role"] == "tenant_admin":
        if job.tenant_id and str(job.tenant_id) != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return job


@router.get("/", response_model=ApplyJobListResponse)
async def list_apply_jobs(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, RUNNING, SUCCESS, FAILED, ROLLED_BACK)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("support")),
):
    """
    List apply jobs with filtering and pagination.
    
    Requires: support, tenant_admin, or platform_admin role
    
    - Tenant admins automatically filtered to their tenant
    - Platform admins and support can view all tenants
    """
    # Auto-filter tenant admins to their own tenant
    if current_user["role"] == "tenant_admin":
        tenant_id = UUID(current_user["tenant_id"]) if current_user.get("tenant_id") else None
    
    result = EnhancedApplyService.list_apply_jobs(
        session=db,
        tenant_id=tenant_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    
    return ApplyJobListResponse(**result)
