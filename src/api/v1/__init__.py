"""API v1 router."""

from fastapi import APIRouter

# Create main v1 router
router = APIRouter()

# Import and include sub-routers
from . import auth, users, tenants, apply, dids

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
router.include_router(apply.router, prefix="/apply", tags=["Apply"])
router.include_router(dids.router, prefix="/dids", tags=["DIDs"])

__all__ = ["router"]
