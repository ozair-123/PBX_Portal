"""Authentication and authorization module."""

from src.auth.password import PasswordHasher, PINHasher
from src.auth.jwt import JWTManager
from src.auth.rbac import (
    get_current_user,
    require_role,
    require_platform_admin,
    require_tenant_admin,
    require_support,
    require_same_tenant,
    require_self_or_admin,
    ROLES,
)

__all__ = [
    "PasswordHasher",
    "PINHasher",
    "JWTManager",
    "get_current_user",
    "require_role",
    "require_platform_admin",
    "require_tenant_admin",
    "require_support",
    "require_same_tenant",
    "require_self_or_admin",
    "ROLES",
]
