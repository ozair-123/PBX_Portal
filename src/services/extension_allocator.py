"""Extension allocation service with tenant-based allocation and row-level locking."""

import secrets
import logging
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.tenant import Tenant

logger = logging.getLogger(__name__)


def generate_sip_secret(length: int = 16) -> str:
    """
    Generate a cryptographically secure SIP secret.

    Args:
        length: Length parameter for token generation (default: 16)

    Returns:
        URL-safe random token suitable for SIP authentication
    """
    return secrets.token_urlsafe(length)


def allocate_extension_for_tenant(session: Session, tenant_id: UUID) -> int:
    """
    Allocate the next available extension for a tenant with row-level locking.

    This function implements race-condition safe allocation by:
    1. Acquiring row-level lock on tenant record (SELECT FOR UPDATE)
    2. Using tenant.ext_next pointer for O(1) allocation
    3. Incrementing ext_next atomically within the locked transaction
    4. Validating extension pool availability

    Args:
        session: SQLAlchemy database session
        tenant_id: UUID of the tenant to allocate extension for

    Returns:
        int: The allocated extension number

    Raises:
        ValueError: If extension pool is exhausted for this tenant
        RuntimeError: If tenant not found

    Example:
        >>> tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        >>> extension = allocate_extension_for_tenant(session, tenant.id)
        >>> user.extension = extension
        >>> session.commit()
    """
    # Acquire row-level lock on tenant to prevent concurrent allocation conflicts
    # FOR UPDATE ensures exclusive access to this tenant row until transaction commits
    tenant = (
        session.query(Tenant)
        .filter(Tenant.id == tenant_id)
        .with_for_update()  # PostgreSQL row-level lock
        .first()
    )

    if not tenant:
        logger.error(f"Tenant {tenant_id} not found during extension allocation")
        raise RuntimeError(f"Tenant {tenant_id} not found")

    # Check if extensions are available in the tenant's pool
    if not tenant.has_available_extensions():
        logger.error(
            f"Extension pool exhausted for tenant {tenant.name} (ID: {tenant_id}): "
            f"range {tenant.ext_min}-{tenant.ext_max} is full"
        )
        raise ValueError(
            f"Extension pool exhausted for tenant '{tenant.name}'. "
            f"All extensions in range {tenant.ext_min}-{tenant.ext_max} are allocated."
        )

    # Allocate next extension and increment pointer atomically
    extension_number = tenant.get_next_extension()

    logger.info(
        f"Successfully allocated extension {extension_number} for tenant {tenant.name} "
        f"(ID: {tenant_id}). Next available: {tenant.ext_next}"
    )

    # Note: Caller must commit the transaction to persist the allocation
    # and release the row lock
    return extension_number
