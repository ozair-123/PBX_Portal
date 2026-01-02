"""User management API endpoints."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.user_service import UserService
from .schemas import (
    CreateUserRequest,
    UserResponse,
    ListUsersResponse,
    DeleteUserResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User created successfully with allocated extension"},
        400: {
            "description": "Validation error (invalid email, empty name, etc.)",
            "model": ErrorResponse
        },
        409: {
            "description": "Email already in use or extension pool exhausted",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Create a new user with auto-allocated extension",
    description=(
        "Creates a new user and automatically allocates an available SIP extension "
        "from the range 1000-1999. The extension allocation is concurrency-safe "
        "with automatic retry on conflicts."
    )
)
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Create a new user with an automatically allocated extension.

    - **name**: User's full name (required, 1-255 characters)
    - **email**: User's email address (required, must be unique, valid email format)

    Returns the created user with extension details including the SIP secret.
    """
    try:
        user_data = UserService.create_user(
            session=db,
            name=request.name,
            email=request.email
        )

        return UserResponse(**user_data)

    except ValueError as e:
        # Validation errors or email already in use
        error_msg = str(e)

        if "already in use" in error_msg.lower():
            logger.warning(f"User creation failed - email conflict: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": error_msg, "details": None}
            )
        elif "pool exhausted" in error_msg.lower():
            logger.error(f"User creation failed - extension pool exhausted: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": error_msg, "details": None}
            )
        else:
            logger.warning(f"User creation failed - validation error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": error_msg, "details": None}
            )

    except RuntimeError as e:
        # Extension allocation retry limit exceeded
        error_msg = str(e)
        logger.error(f"User creation failed - allocation error: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": error_msg,
                "details": "High contention detected during extension allocation"
            }
        )

    except Exception as e:
        # Unexpected server errors
        logger.exception(f"Unexpected error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "details": "An unexpected error occurred while creating the user"
            }
        )


@router.get(
    "",
    response_model=ListUsersResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "List of all users retrieved successfully"},
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="List all users",
    description="Retrieves all users with their assigned extensions for operational visibility."
)
async def list_users(db: Session = Depends(get_db)) -> ListUsersResponse:
    """
    Retrieve all users with their assigned extensions.

    Returns a list of all users in the system with their extension details.
    """
    try:
        users = UserService.list_all_users(session=db)
        return ListUsersResponse(users=users)

    except RuntimeError as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to retrieve users",
                "details": str(e)
            }
        )

    except Exception as e:
        logger.exception(f"Unexpected error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "details": "An unexpected error occurred while retrieving users"
            }
        )


@router.delete(
    "/{user_id}",
    response_model=DeleteUserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "User deleted successfully, extension freed"},
        404: {
            "description": "User not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    },
    summary="Delete a user",
    description=(
        "Deletes a user and frees their extension for reuse. "
        "The extension is automatically deleted via CASCADE relationship."
    )
)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db)
) -> DeleteUserResponse:
    """
    Delete a user and free their extension.

    - **user_id**: UUID of the user to delete

    Returns confirmation with the freed extension number.
    """
    try:
        result = UserService.delete_user(session=db, user_id=user_id)
        return DeleteUserResponse(**result)

    except ValueError as e:
        # User not found
        logger.warning(f"User deletion failed - not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": str(e), "details": None}
        )

    except RuntimeError as e:
        # Database errors
        logger.error(f"User deletion failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to delete user",
                "details": str(e)
            }
        )

    except Exception as e:
        logger.exception(f"Unexpected error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "details": "An unexpected error occurred while deleting the user"
            }
        )
