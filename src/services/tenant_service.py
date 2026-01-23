"""Tenant service for managing tenant operations."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.tenant import Tenant, TenantStatus


class TenantService:
    """Service for tenant management operations."""

    @staticmethod
    def create_tenant(
        session: Session,
        name: str,
        ext_min: int,
        ext_max: int,
        default_inbound_destination: Optional[str] = None,
        outbound_policy_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tenant:
        """
        Create a new tenant.

        Args:
            session: Database session
            name: Tenant name
            ext_min: Minimum extension number
            ext_max: Maximum extension number
            default_inbound_destination: Optional default inbound routing
            outbound_policy_id: Optional default outbound policy
            actor_id: Optional user ID performing the action (for audit)
            source_ip: Optional client IP (for audit)
            user_agent: Optional user agent (for audit)

        Returns:
            Created Tenant object
        """
        tenant = Tenant(
            name=name,
            ext_min=ext_min,
            ext_max=ext_max,
            ext_next=ext_min,  # Start at minimum extension
            default_inbound_destination=default_inbound_destination,
            outbound_policy_id=outbound_policy_id,
            status=TenantStatus.active,
        )
        session.add(tenant)
        session.flush()
        return tenant

    @staticmethod
    def get_tenant(session: Session, tenant_id: UUID) -> Optional[Tenant]:
        """
        Get a tenant by ID.

        Args:
            session: Database session
            tenant_id: Tenant UUID

        Returns:
            Tenant object or None if not found
        """
        return session.query(Tenant).filter(Tenant.id == tenant_id).first()

    @staticmethod
    def list_tenants(
        session: Session,
        status: Optional[TenantStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """
        List tenants with optional filtering.

        Args:
            session: Database session
            status: Optional status filter
            search: Optional name search
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dict with tenants, total, page, page_size
        """
        query = session.query(Tenant)

        if status:
            query = query.filter(Tenant.status == status)

        if search:
            query = query.filter(Tenant.name.ilike(f"%{search}%"))

        total = query.count()
        offset = (page - 1) * page_size
        tenants = query.order_by(Tenant.created_at.desc()).limit(page_size).offset(offset).all()

        return {
            "tenants": tenants,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def update_tenant(
        session: Session,
        tenant_id: UUID,
        name: Optional[str] = None,
        ext_min: Optional[int] = None,
        ext_max: Optional[int] = None,
        default_inbound_destination: Optional[str] = None,
        outbound_policy_id: Optional[UUID] = None,
        status: Optional[TenantStatus] = None,
    ) -> Optional[Tenant]:
        """
        Update a tenant.

        Args:
            session: Database session
            tenant_id: Tenant UUID
            name: Optional new name
            ext_min: Optional new minimum extension
            ext_max: Optional new maximum extension
            default_inbound_destination: Optional new default inbound routing
            outbound_policy_id: Optional new outbound policy
            status: Optional new status

        Returns:
            Updated Tenant object or None if not found
        """
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return None

        if name is not None:
            tenant.name = name
        if ext_min is not None:
            tenant.ext_min = ext_min
        if ext_max is not None:
            tenant.ext_max = ext_max
        if default_inbound_destination is not None:
            tenant.default_inbound_destination = default_inbound_destination
        if outbound_policy_id is not None:
            tenant.outbound_policy_id = outbound_policy_id
        if status is not None:
            tenant.status = status

        session.flush()
        return tenant

    @staticmethod
    def delete_tenant(session: Session, tenant_id: UUID) -> bool:
        """
        Delete a tenant.

        Args:
            session: Database session
            tenant_id: Tenant UUID

        Returns:
            True if deleted, False if not found
        """
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False

        session.delete(tenant)
        session.flush()
        return True
