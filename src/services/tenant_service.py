"""Tenant service for multi-tenancy management."""

import logging
from uuid import UUID
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models.tenant import Tenant, TenantStatus
from ..services.audit_service import AuditService

logger = logging.getLogger(__name__)


class TenantService:
    """
    Service for tenant provisioning and management.
    
    Handles:
    - Tenant creation with extension range setup
    - Tenant updates
    - Tenant status management
    - Tenant search and filtering
    """
    
    @staticmethod
    def create_tenant(
        session: Session,
        name: str,
        ext_min: int,
        ext_max: int,
        actor_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> Tenant:
        """
        Create a new tenant with extension range.
        
        Args:
            session: Database session
            name: Tenant name (must be unique)
            ext_min: Minimum extension number
            ext_max: Maximum extension number
            actor_id: ID of user performing the action
            source_ip: Source IP address
            user_agent: User agent string
            **kwargs: Additional tenant fields
        
        Returns:
            Tenant: Created tenant object
        
        Raises:
            ValueError: If name already exists or range is invalid
        """
        # Check if name already exists
        existing = session.query(Tenant).filter(Tenant.name == name).first()
        if existing:
            raise ValueError(f"Tenant name '{name}' already exists")
        
        # Validate extension range
        if ext_min >= ext_max:
            raise ValueError(f"ext_min ({ext_min}) must be less than ext_max ({ext_max})")
        
        if ext_min < 1000 or ext_max > 99999:
            raise ValueError("Extension range must be between 1000 and 99999")
        
        # Create tenant
        tenant = Tenant(
            name=name,
            ext_min=ext_min,
            ext_max=ext_max,
            ext_next=ext_min,  # Start from minimum
            **kwargs
        )
        
        session.add(tenant)
        session.flush()
        
        # Create audit log
        if actor_id:
            after_state = AuditService.entity_to_dict(tenant)
            AuditService.log_create(
                session=session,
                actor_id=actor_id,
                entity_type="Tenant",
                entity_id=tenant.id,
                after_state=after_state,
                tenant_id=None,  # No tenant ID for tenant creation
                source_ip=source_ip,
                user_agent=user_agent,
            )
        
        logger.info(f"Created tenant '{name}' with extension range {ext_min}-{ext_max}")
        return tenant
    
    @staticmethod
    def update_tenant(
        session: Session,
        tenant_id: UUID,
        actor_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **updates
    ) -> Tenant:
        """
        Update an existing tenant.
        
        Args:
            session: Database session
            tenant_id: Tenant ID to update
            actor_id: ID of user performing the action
            source_ip: Source IP address
            user_agent: User agent string
            **updates: Fields to update
        
        Returns:
            Tenant: Updated tenant object
        
        Raises:
            ValueError: If tenant not found or name already exists
        """
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Capture before state
        before_state = AuditService.entity_to_dict(tenant) if actor_id else None
        
        # Check name uniqueness if updating
        if 'name' in updates:
            existing = session.query(Tenant).filter(
                Tenant.name == updates['name'],
                Tenant.id != tenant_id
            ).first()
            if existing:
                raise ValueError(f"Tenant name '{updates['name']}' already exists")
        
        # Validate extension range if updating
        ext_min = updates.get('ext_min', tenant.ext_min)
        ext_max = updates.get('ext_max', tenant.ext_max)
        
        if ext_min >= ext_max:
            raise ValueError(f"ext_min ({ext_min}) must be less than ext_max ({ext_max})")
        
        # Convert status string to enum
        if 'status' in updates:
            updates['status'] = TenantStatus[updates['status']]
        
        # Update fields
        for field, value in updates.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)
        
        session.flush()
        
        # Create audit log
        if actor_id:
            after_state = AuditService.entity_to_dict(tenant)
            AuditService.log_update(
                session=session,
                actor_id=actor_id,
                entity_type="Tenant",
                entity_id=tenant.id,
                before_state=before_state,
                after_state=after_state,
                tenant_id=None,
                source_ip=source_ip,
                user_agent=user_agent,
            )
        
        logger.info(f"Updated tenant '{tenant.name}'")
        return tenant
    
    @staticmethod
    def get_tenant(session: Session, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        return session.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    @staticmethod
    def list_tenants(
        session: Session,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        List tenants with filtering and pagination.
        
        Args:
            session: Database session
            status: Filter by status (active, suspended)
            page: Page number (1-indexed)
            page_size: Items per page
        
        Returns:
            dict: {tenants: List[Tenant], total: int, page: int, page_size: int}
        """
        query = session.query(Tenant)
        
        # Apply filters
        if status:
            query = query.filter(Tenant.status == TenantStatus[status])
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        tenants = query.order_by(Tenant.created_at.desc()).offset(offset).limit(page_size).all()
        
        return {
            "tenants": tenants,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
