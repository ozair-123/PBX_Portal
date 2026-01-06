"""User service for business logic and operations."""

import logging
from uuid import UUID
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.user import User, UserRole, UserStatus
from ..models.tenant import Tenant
from ..auth.password import PasswordHasher, PINHasher
from ..services.extension_allocator import allocate_extension_for_tenant
from ..services.audit_service import AuditService

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user provisioning and management.

    Handles:
    - User creation with automatic extension assignment
    - User updates with audit logging
    - User deletion (soft delete)
    - User search and filtering
    """

    @staticmethod
    def create_user(
        session: Session,
        tenant_id: UUID,
        name: str,
        email: str,
        password: str,
        role: str = "end_user",
        actor_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> User:
        """
        Create a new user with automatic extension assignment.

        Args:
            session: Database session
            tenant_id: Tenant ID
            name: Full name
            email: Email address (must be unique)
            password: Plain text password (will be hashed)
            role: User role (default: end_user)
            actor_id: ID of user performing the action (for audit)
            source_ip: Source IP address
            user_agent: User agent string
            **kwargs: Additional user fields (outbound_callerid, voicemail_enabled, etc.)

        Returns:
            User: Created user object

        Raises:
            ValueError: If email already exists or tenant not found
            RuntimeError: If extension allocation fails
        """
        # Check if email already exists
        existing_user = session.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError(f"Email {email} already exists")

        # Verify tenant exists
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Allocate extension for the user
        try:
            extension_number = allocate_extension_for_tenant(session, tenant_id)
        except Exception as e:
            logger.error(f"Failed to allocate extension: {str(e)}")
            raise RuntimeError(f"Extension allocation failed: {str(e)}")

        # Hash password
        password_hash = PasswordHasher.hash(password)

        # Hash voicemail PIN if provided
        voicemail_pin = kwargs.pop('voicemail_pin', None)
        voicemail_pin_hash = None
        if voicemail_pin:
            voicemail_pin_hash = PINHasher.hash(voicemail_pin)

        # Create user
        user = User(
            tenant_id=tenant_id,
            name=name,
            email=email,
            password_hash=password_hash,
            role=UserRole[role],
            extension=extension_number,
            voicemail_pin_hash=voicemail_pin_hash,
            **kwargs
        )

        session.add(user)
        session.flush()  # Get user ID before audit log

        # Create audit log
        if actor_id:
            after_state = AuditService.entity_to_dict(
                user,
                exclude_fields=['password_hash', 'voicemail_pin_hash']
            )
            AuditService.log_create(
                session=session,
                actor_id=actor_id,
                entity_type="User",
                entity_id=user.id,
                after_state=after_state,
                tenant_id=tenant_id,
                source_ip=source_ip,
                user_agent=user_agent,
            )

        logger.info(f"Created user {email} with extension {extension_number}")
        return user

    @staticmethod
    def update_user(
        session: Session,
        user_id: UUID,
        actor_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **updates
    ) -> User:
        """
        Update an existing user.

        Args:
            session: Database session
            user_id: User ID to update
            actor_id: ID of user performing the action
            source_ip: Source IP address
            user_agent: User agent string
            **updates: Fields to update (name, email, password, role, etc.)

        Returns:
            User: Updated user object

        Raises:
            ValueError: If user not found or email already exists
        """
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Capture before state for audit
        before_state = AuditService.entity_to_dict(
            user,
            exclude_fields=['password_hash', 'voicemail_pin_hash']
        ) if actor_id else None

        # Check email uniqueness if updating
        if 'email' in updates:
            existing = session.query(User).filter(
                User.email == updates['email'],
                User.id != user_id
            ).first()
            if existing:
                raise ValueError(f"Email {updates['email']} already exists")

        # Hash password if updating
        if 'password' in updates:
            updates['password_hash'] = PasswordHasher.hash(updates.pop('password'))

        # Hash voicemail PIN if updating
        if 'voicemail_pin' in updates:
            pin = updates.pop('voicemail_pin')
            updates['voicemail_pin_hash'] = PINHasher.hash(pin) if pin else None

        # Convert role/status strings to enums
        if 'role' in updates:
            updates['role'] = UserRole[updates['role']]
        if 'status' in updates:
            updates['status'] = UserStatus[updates['status']]

        # Update fields
        for field, value in updates.items():
            if hasattr(user, field):
                setattr(user, field, value)

        session.flush()

        # Create audit log
        if actor_id:
            after_state = AuditService.entity_to_dict(
                user,
                exclude_fields=['password_hash', 'voicemail_pin_hash']
            )
            AuditService.log_update(
                session=session,
                actor_id=actor_id,
                entity_type="User",
                entity_id=user.id,
                before_state=before_state,
                after_state=after_state,
                tenant_id=user.tenant_id,
                source_ip=source_ip,
                user_agent=user_agent,
            )

        logger.info(f"Updated user {user.email}")
        return user

    @staticmethod
    def delete_user(
        session: Session,
        user_id: UUID,
        actor_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """
        Soft delete a user (set status to deleted).

        Args:
            session: Database session
            user_id: User ID to delete
            actor_id: ID of user performing the action
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            User: Deleted user object

        Raises:
            ValueError: If user not found
        """
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Capture before state
        before_state = AuditService.entity_to_dict(
            user,
            exclude_fields=['password_hash', 'voicemail_pin_hash']
        ) if actor_id else None

        # Soft delete
        user.status = UserStatus.deleted
        session.flush()

        # Create audit log
        if actor_id:
            AuditService.log_delete(
                session=session,
                actor_id=actor_id,
                entity_type="User",
                entity_id=user.id,
                before_state=before_state,
                tenant_id=user.tenant_id,
                source_ip=source_ip,
                user_agent=user_agent,
            )

        logger.info(f"Deleted user {user.email}")
        return user

    @staticmethod
    def get_user(session: Session, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return session.query(User).filter(User.id == user_id).first()

    @staticmethod
    def list_users(
        session: Session,
        tenant_id: Optional[UUID] = None,
        status: Optional[str] = None,
        role: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        List users with optional filtering and pagination.

        Args:
            session: Database session
            tenant_id: Filter by tenant ID
            status: Filter by status (active, suspended, deleted)
            role: Filter by role
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            dict: {users: List[User], total: int, page: int, page_size: int}
        """
        query = session.query(User)

        # Apply filters
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        if status:
            query = query.filter(User.status == UserStatus[status])
        if role:
            query = query.filter(User.role == UserRole[role])

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
