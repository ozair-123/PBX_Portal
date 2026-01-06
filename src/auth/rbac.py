"""
Role-Based Access Control (RBAC) decorators.

This module provides role enforcement for API endpoints with 4 roles:
- platform_admin: Full system access, manage all tenants
- tenant_admin: Manage users, devices, DIDs, policies within own tenant
- support: Read-only access to tenant resources for troubleshooting
- end_user: Self-service only (DND, call forwarding, voicemail)
"""

from functools import wraps
from typing import Callable, Dict
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.auth.jwt import JWTManager

# Security scheme for Bearer token
security = HTTPBearer()

# Role hierarchy (higher number = more privileges)
ROLES = {
    "platform_admin": 4,
    "tenant_admin": 3,
    "support": 2,
    "end_user": 1,
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials (Bearer token)

    Returns:
        User payload dict with user_id, role, tenant_id (if applicable)

    Raises:
        HTTPException 401: If token is invalid or expired
        HTTPException 403: If user is not authorized

    Example:
        >>> @router.get("/protected")
        >>> async def protected_endpoint(
        ...     current_user: Dict = Depends(get_current_user)
        ... ):
        ...     return {"user_id": current_user["user_id"]}
    """
    token = credentials.credentials
    payload = JWTManager.verify_token(token, token_type="access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user info from token
    user_id = payload.get("user_id")
    role = payload.get("role")
    tenant_id = payload.get("tenant_id")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "role": role,
        "tenant_id": tenant_id,
    }


def require_role(minimum_role: str) -> Callable:
    """
    Decorator factory to enforce minimum role requirement.

    Args:
        minimum_role: Minimum role required (platform_admin, tenant_admin, support, end_user)

    Returns:
        Dependency function for FastAPI

    Raises:
        HTTPException 403: If user's role is below minimum required

    Example:
        >>> @router.post("/users")
        >>> async def create_user(
        ...     user_data: UserCreate,
        ...     current_user: Dict = Depends(require_role("tenant_admin"))
        ... ):
        ...     # Only tenant_admin or platform_admin can access
        ...     return {"created": True}
    """
    def role_checker(current_user: Dict = Depends(get_current_user)) -> Dict:
        user_role = current_user.get("role")
        user_role_level = ROLES.get(user_role, 0)
        required_level = ROLES.get(minimum_role, 999)

        if user_role_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {minimum_role}, your role: {user_role}",
            )

        return current_user

    return role_checker


def require_platform_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to require platform_admin role.

    Args:
        current_user: Current authenticated user

    Returns:
        User payload dict

    Raises:
        HTTPException 403: If user is not platform_admin

    Example:
        >>> @router.post("/tenants")
        >>> async def create_tenant(
        ...     tenant_data: TenantCreate,
        ...     current_user: Dict = Depends(require_platform_admin)
        ... ):
        ...     # Only platform_admin can create tenants
        ...     return {"created": True}
    """
    if current_user.get("role") != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return current_user


def require_tenant_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to require tenant_admin role (or higher).

    Args:
        current_user: Current authenticated user

    Returns:
        User payload dict

    Raises:
        HTTPException 403: If user is not tenant_admin or platform_admin

    Example:
        >>> @router.post("/users")
        >>> async def create_user(
        ...     user_data: UserCreate,
        ...     current_user: Dict = Depends(require_tenant_admin)
        ... ):
        ...     # Tenant admin or platform admin can create users
        ...     return {"created": True}
    """
    role = current_user.get("role")
    if ROLES.get(role, 0) < ROLES["tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin access required",
        )
    return current_user


def require_support(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to require support role (or higher).

    Args:
        current_user: Current authenticated user

    Returns:
        User payload dict

    Raises:
        HTTPException 403: If user is below support role

    Example:
        >>> @router.get("/diagnostics")
        >>> async def get_diagnostics(
        ...     current_user: Dict = Depends(require_support)
        ... ):
        ...     # Support, tenant admin, or platform admin can view diagnostics
        ...     return {"status": "healthy"}
    """
    role = current_user.get("role")
    if ROLES.get(role, 0) < ROLES["support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Support access required",
        )
    return current_user


def require_same_tenant(current_user: Dict = Depends(get_current_user)) -> Callable:
    """
    Decorator factory to enforce tenant isolation.

    Ensures user can only access resources in their own tenant
    (unless they are platform_admin).

    Args:
        current_user: Current authenticated user

    Returns:
        Validator function

    Example:
        >>> @router.get("/users/{user_id}")
        >>> async def get_user(
        ...     user_id: str,
        ...     current_user: Dict = Depends(require_same_tenant)
        ... ):
        ...     # Fetch user from database
        ...     user = get_user_by_id(user_id)
        ...     # Validate tenant matches
        ...     if user.tenant_id != current_user["tenant_id"]:
        ...         # This check is done by require_same_tenant
        ...         raise HTTPException(403, "Cannot access other tenant's resources")
    """
    def validate_tenant_access(resource_tenant_id: str):
        """
        Validate user can access resource in given tenant.

        Args:
            resource_tenant_id: Tenant ID of the resource being accessed

        Raises:
            HTTPException 403: If user cannot access resource
        """
        # Platform admins can access all tenants
        if current_user.get("role") == "platform_admin":
            return

        # Other users can only access their own tenant
        user_tenant_id = current_user.get("tenant_id")
        if user_tenant_id != resource_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access resources from another tenant",
            )

    return validate_tenant_access


def require_self_or_admin(current_user: Dict = Depends(get_current_user)) -> Callable:
    """
    Decorator factory to enforce self-access or admin access.

    Allows users to access their own resources, or admins to access any user's resources.

    Args:
        current_user: Current authenticated user

    Returns:
        Validator function

    Example:
        >>> @router.get("/users/{user_id}")
        >>> async def get_user(
        ...     user_id: str,
        ...     current_user: Dict = Depends(require_self_or_admin)
        ... ):
        ...     # User can access their own profile, or admin can access any profile
        ...     return {"user_id": user_id}
    """
    def validate_self_or_admin_access(resource_user_id: str):
        """
        Validate user can access resource owned by given user.

        Args:
            resource_user_id: User ID of the resource owner

        Raises:
            HTTPException 403: If user cannot access resource
        """
        user_id = current_user.get("user_id")
        role = current_user.get("role")

        # Users can access their own resources
        if user_id == resource_user_id:
            return

        # Admins can access any user's resources (within their tenant)
        if ROLES.get(role, 0) >= ROLES["tenant_admin"]:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's resources",
        )

    return validate_self_or_admin_access
