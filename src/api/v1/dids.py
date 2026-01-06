"""API endpoints for DID (Direct Inward Dialing) management."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.auth.rbac import require_role, get_current_user
from src.models.user import User
from src.schemas.phone_number import (
    DIDImportRequest,
    DIDImportResponse,
    DIDAllocateRequest,
    PhoneNumberResponse,
    DIDAssignRequest,
    DIDAssignmentResponse
)
from src.services.did_service import DIDService
from src.database import get_db


router = APIRouter()


@router.post(
    "/import",
    response_model=DIDImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import DIDs into global pool",
    description="Bulk import phone numbers (DIDs) from carrier into the global pool. "
                "Requires platform_admin role. All DIDs will be created with UNASSIGNED status.",
    responses={
        201: {
            "description": "DIDs imported successfully",
            "content": {
                "application/json": {
                    "example": {
                        "imported": 100,
                        "failed": 0,
                        "errors": []
                    }
                }
            }
        },
        400: {
            "description": "Validation errors (invalid E.164 format or duplicate numbers)",
            "content": {
                "application/json": {
                    "example": {
                        "imported": 0,
                        "failed": 2,
                        "errors": [
                            {"number": "+1234", "error": "Invalid E.164 format"},
                            {"number": "+15551234567", "error": "Duplicate number already exists"}
                        ]
                    }
                }
            }
        },
        403: {"description": "Forbidden - requires platform_admin role"},
        500: {"description": "Internal server error during import"}
    }
)
async def import_dids(
    request: Request,
    import_request: DIDImportRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("platform_admin"))]
):
    """
    Import multiple DIDs into the global pool.

    **Authorization**: Requires `platform_admin` role.

    **Request Body**:
    - `dids`: List of DIDs to import (max 10,000)
        - `number`: Phone number in E.164 format (e.g., +15551234567)
        - `provider`: Provider name (optional)
        - `provider_metadata`: Provider-specific metadata (optional)

    **Validation**:
    - All numbers must be in valid E.164 format
    - Numbers must not already exist in the database
    - If any validation fails, NO DIDs are imported (atomic operation)

    **Returns**:
    - `imported`: Number of DIDs successfully imported
    - `failed`: Number of DIDs that failed validation
    - `errors`: List of validation errors with details
    """
    try:
        # Extract source IP and user agent for audit logging
        source_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Call DIDService to import DIDs
        imported_count, errors = DIDService.import_dids(
            db=db,
            dids=import_request.dids,
            actor_id=current_user.id,
            source_ip=source_ip,
            user_agent=user_agent
        )

        # If there were validation errors, return 400 with error details
        if errors:
            return DIDImportResponse(
                imported=0,
                failed=len(errors),
                errors=errors
            )

        # Success case
        return DIDImportResponse(
            imported=imported_count,
            failed=0,
            errors=[]
        )

    except ValueError as e:
        # Validation errors (400 Bad Request)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        # Database or system errors (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import DIDs: {str(e)}"
        )
    except Exception as e:
        # Unexpected errors (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during DID import: {str(e)}"
        )


@router.post(
    "/{phone_number_id}/allocate",
    response_model=PhoneNumberResponse,
    summary="Allocate DID to tenant",
    description="Allocate an UNASSIGNED phone number to a specific tenant. "
                "Requires platform_admin role. Status changes from UNASSIGNED to ALLOCATED.",
    responses={
        200: {"description": "DID allocated successfully"},
        400: {"description": "Invalid status transition or phone number not found"},
        403: {"description": "Forbidden - requires platform_admin role"},
        500: {"description": "Internal server error"}
    }
)
async def allocate_did(
    request: Request,
    phone_number_id: UUID,
    allocate_request: DIDAllocateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("platform_admin"))]
):
    """
    Allocate an UNASSIGNED phone number to a tenant.

    **Authorization**: Requires `platform_admin` role.

    **Path Parameters**:
    - `phone_number_id`: UUID of the phone number to allocate

    **Request Body**:
    - `tenant_id`: UUID of the tenant to allocate to

    **Status Transition**: UNASSIGNED → ALLOCATED
    """
    try:
        source_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        phone_number = DIDService.allocate_to_tenant(
            db=db,
            phone_number_id=phone_number_id,
            tenant_id=allocate_request.tenant_id,
            actor_id=current_user.id,
            source_ip=source_ip,
            user_agent=user_agent
        )

        return PhoneNumberResponse.model_validate(phone_number)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/{phone_number_id}/assign",
    response_model=DIDAssignmentResponse,
    summary="Assign DID to destination",
    description="Assign an ALLOCATED phone number to a destination (user, IVR, queue, or external dialplan). "
                "Requires tenant_admin role. Tenant admin can only assign DIDs within their tenant. "
                "Status changes from ALLOCATED to ASSIGNED.",
    responses={
        201: {"description": "DID assigned successfully"},
        400: {"description": "Invalid request (wrong status, tenant mismatch, validation error)"},
        403: {"description": "Forbidden - requires tenant_admin role or not your tenant's DID"},
        404: {"description": "Phone number or user not found"},
        409: {"description": "Conflict - DID already assigned"},
        500: {"description": "Internal server error"}
    }
)
async def assign_did(
    request: Request,
    phone_number_id: UUID,
    assign_request: DIDAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("tenant_admin"))]
):
    """
    Assign an ALLOCATED phone number to a destination.

    **Authorization**: Requires `tenant_admin` role. Tenant admins can only assign DIDs within their tenant.

    **Path Parameters**:
    - `phone_number_id`: UUID of the phone number to assign

    **Request Body**:
    - `assigned_type`: Type of destination (USER, IVR, QUEUE, EXTERNAL)
    - `assigned_id`: UUID of destination entity (required for USER, IVR, QUEUE)
    - `assigned_value`: Dialplan context string (required for EXTERNAL)

    **Status Transition**: ALLOCATED → ASSIGNED

    **Validation**:
    - Phone number must be ALLOCATED
    - For USER: user must exist and belong to same tenant
    - Tenant admin can only assign DIDs allocated to their tenant
    """
    try:
        source_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Fetch phone number to check tenant ownership
        from src.models import PhoneNumber
        phone_number = db.query(PhoneNumber).filter(
            PhoneNumber.id == phone_number_id
        ).first()

        if not phone_number:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phone number not found: {phone_number_id}"
            )

        # Authorization check: tenant admin can only assign DIDs in their tenant
        if phone_number.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only assign DIDs within your tenant"
            )

        # Call DIDService to perform assignment
        assignment = DIDService.assign_to_destination(
            db=db,
            phone_number_id=phone_number_id,
            assigned_type=assign_request.assigned_type,
            assigned_id=assign_request.assigned_id,
            assigned_value=assign_request.assigned_value,
            actor_id=current_user.id,
            source_ip=source_ip,
            user_agent=user_agent
        )

        return DIDAssignmentResponse.model_validate(assignment)

    except ValueError as e:
        # Validation errors (phone not found, wrong status, tenant mismatch, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except IntegrityError as e:
        # Duplicate assignment (unique constraint violation)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except RuntimeError as e:
        # Database or system errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/{phone_number_id}/assign",
    response_model=PhoneNumberResponse,
    summary="Unassign DID from destination",
    description="Remove assignment from a phone number, returning it to ALLOCATED status. "
                "Requires tenant_admin role. Status changes from ASSIGNED to ALLOCATED.",
    responses={
        200: {"description": "DID unassigned successfully"},
        400: {"description": "Invalid request (phone not ASSIGNED or not found)"},
        403: {"description": "Forbidden - requires tenant_admin role or not your tenant's DID"},
        404: {"description": "Phone number not found"},
        500: {"description": "Internal server error"}
    }
)
async def unassign_did(
    request: Request,
    phone_number_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("tenant_admin"))]
):
    """
    Unassign a phone number from its destination.

    **Authorization**: Requires `tenant_admin` role. Tenant admins can only unassign DIDs within their tenant.

    **Path Parameters**:
    - `phone_number_id`: UUID of the phone number to unassign

    **Status Transition**: ASSIGNED → ALLOCATED

    **Effect**:
    - Deletes the DIDAssignment record
    - Returns phone number to ALLOCATED status
    - Phone number remains allocated to the tenant
    """
    try:
        source_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Fetch phone number to check tenant ownership
        from src.models import PhoneNumber
        phone_number = db.query(PhoneNumber).filter(
            PhoneNumber.id == phone_number_id
        ).first()

        if not phone_number:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phone number not found: {phone_number_id}"
            )

        # Authorization check: tenant admin can only unassign DIDs in their tenant
        if phone_number.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only unassign DIDs within your tenant"
            )

        # Call DIDService to perform unassignment
        phone_number = DIDService.unassign(
            db=db,
            phone_number_id=phone_number_id,
            actor_id=current_user.id,
            source_ip=source_ip,
            user_agent=user_agent
        )

        return PhoneNumberResponse.model_validate(phone_number)

    except ValueError as e:
        # Validation errors (phone not found, wrong status, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        # Database or system errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
