"""Authentication endpoints - login, refresh, logout."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from ...auth.password import PasswordHasher
from ...auth.jwt import JWTManager
from ...auth.rbac import get_current_user
from ...models.user import User, UserStatus
from ...services.audit_service import AuditService
from ...database import get_db

router = APIRouter()
security = HTTPBearer()


# Request/Response models
class LoginRequest(BaseModel):
    """Login request payload."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response payload."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class RefreshRequest(BaseModel):
    """Refresh token request payload."""
    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return access/refresh tokens.

    Args:
        request: FastAPI request object (for IP/user agent)
        credentials: Email and password
        db: Database session

    Returns:
        TokenResponse with access_token, refresh_token, token_type, expires_in

    Raises:
        401: Invalid credentials or user not active
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not PasswordHasher.verify(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account is {user.status.value}. Please contact support.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token pair
    tokens = JWTManager.create_token_pair(
        user_id=str(user.id),
        role=user.role.value,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )

    # Log login event
    source_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    AuditService.log_login(
        session=db,
        actor_id=user.id,
        tenant_id=user.tenant_id,
        source_ip=source_ip,
        user_agent=user_agent,
    )

    db.commit()

    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Args:
        refresh_request: Refresh token payload
        db: Database session

    Returns:
        TokenResponse with new access_token and same refresh_token

    Raises:
        401: Invalid or expired refresh token
        404: User not found
    """
    # Verify refresh token
    payload = JWTManager.verify_token(refresh_request.refresh_token, token_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if user is still active
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account is {user.status.value}. Please contact support.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new token pair
    tokens = JWTManager.create_token_pair(
        user_id=str(user.id),
        role=user.role.value,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )

    return TokenResponse(**tokens)


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Logout user (invalidate session).

    Note: Since we use stateless JWT, logout is primarily for audit logging.
    Clients should discard tokens on logout. For true token invalidation,
    implement a token blacklist (future enhancement).

    Args:
        request: FastAPI request object (for IP/user agent)
        current_user: Current authenticated user (from JWT)
        db: Database session

    Returns:
        MessageResponse confirming logout
    """
    # Log logout event
    source_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    AuditService.log_logout(
        session=db,
        actor_id=current_user["user_id"],
        tenant_id=current_user.get("tenant_id"),
        source_ip=source_ip,
        user_agent=user_agent,
    )

    db.commit()

    return MessageResponse(message="Successfully logged out")


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user (from JWT)
        db: Database session

    Returns:
        User object (without sensitive fields)

    Raises:
        404: User not found
    """
    user = db.query(User).filter(User.id == current_user["user_id"]).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Return user info (excluding sensitive fields)
    return {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "status": user.status.value,
        "extension": user.extension,
        "outbound_callerid": user.outbound_callerid,
        "voicemail_enabled": user.voicemail_enabled,
        "dnd_enabled": user.dnd_enabled,
        "call_forward_destination": user.call_forward_destination,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }
