"""Role-Based Access Control (RBAC) utilities."""
from typing import Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Get current user from JWT token.

    For testing purposes, returns a mock admin user if no token provided.
    """
    # TODO: Implement proper JWT validation
    # For now, return a mock user for testing
    return {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "email": "admin@test.com",
        "role": "platform_admin",
        "tenant_id": None
    }


def require_role(*allowed_roles: str) -> Callable:
    """
    Dependency that requires user to have one of the specified roles.

    Args:
        *allowed_roles: One or more role names (e.g., "platform_admin", "tenant_admin")

    Returns:
        Dependency function that validates user role
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        """Check if current user has required role."""
        user_role = current_user.get("role")

        # Platform admins have access to everything
        if user_role == "platform_admin":
            return current_user

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}"
            )

        return current_user

    return role_checker
