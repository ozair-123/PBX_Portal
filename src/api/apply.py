"""Apply configuration API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.apply_service import ApplyService
from .schemas import (
    ApplyRequest,
    ApplyResponse,
    ApplyErrorResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ApplyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Configuration applied successfully to Asterisk"},
        409: {
            "description": "Conflict - another apply operation is in progress",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error or Asterisk reload failure",
            "model": ApplyErrorResponse
        }
    },
    summary="Apply configuration to Asterisk",
    description=(
        "Applies the current database configuration to the live Asterisk server. "
        "This operation:\n"
        "1. Acquires an advisory lock to prevent concurrent apply operations\n"
        "2. Reads all users and extensions from the database\n"
        "3. Generates PJSIP and dialplan configuration files\n"
        "4. Writes files atomically to /etc/asterisk/\n"
        "5. Reloads Asterisk PJSIP and dialplan modules\n"
        "6. Creates an audit log entry\n\n"
        "This operation is serialized - only one apply can run at a time."
    )
)
async def apply_configuration(
    request: ApplyRequest,
    db: Session = Depends(get_db)
) -> ApplyResponse:
    """
    Apply database configuration to Asterisk.

    - **triggered_by**: Username or identifier of who triggered this apply operation

    Returns audit log ID, files written, reload results, and counts of users/extensions applied.
    """
    try:
        result = ApplyService.apply_configuration(
            session=db,
            triggered_by=request.triggered_by
        )

        return ApplyResponse(
            message="Configuration applied successfully",
            audit_log_id=result["audit_log_id"],
            files_written=result["files_written"],
            reload_results=result["reload_results"],
            users_applied=result["users_applied"],
            extensions_generated=result["extensions_generated"]
        )

    except RuntimeError as e:
        error_msg = str(e)

        # Check if this is a lock conflict (another apply in progress)
        if "in progress" in error_msg.lower():
            logger.warning(f"Apply failed - concurrent operation: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": error_msg,
                    "details": "Wait for the current apply operation to complete and try again"
                }
            )
        else:
            # Other runtime errors (reload failures, etc.)
            logger.error(f"Apply failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": error_msg,
                    "audit_log_id": None,
                    "details": None
                }
            )

    except PermissionError as e:
        # File write or asterisk command permission errors
        error_msg = str(e)
        logger.error(f"Apply failed - permission error: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Permission denied",
                "audit_log_id": None,
                "details": error_msg
            }
        )

    except FileNotFoundError as e:
        # Asterisk command not found
        error_msg = str(e)
        logger.error(f"Apply failed - asterisk not found: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Asterisk command not found",
                "audit_log_id": None,
                "details": error_msg
            }
        )

    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error during apply: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "audit_log_id": None,
                "details": "An unexpected error occurred during configuration apply"
            }
        )
