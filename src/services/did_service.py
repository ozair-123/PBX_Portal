"""Service layer for DID (Direct Inward Dialing) management."""
import re
from typing import List, Tuple, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models import PhoneNumber, PhoneNumberStatus, DIDAssignment, AssignmentType
from src.services.audit_service import AuditService
from src.schemas.phone_number import DIDImportItem, DIDImportError


# E.164 validation pattern
E164_REGEX = re.compile(r'^\+[1-9]\d{1,14}$')


class DIDService:
    """Service for managing phone numbers (DIDs) and their assignments."""

    @staticmethod
    def validate_e164(number: str) -> bool:
        """
        Validate if a phone number is in E.164 format.

        Args:
            number: Phone number string to validate

        Returns:
            True if valid E.164 format, False otherwise

        Example:
            >>> DIDService.validate_e164("+15551234567")
            True
            >>> DIDService.validate_e164("5551234567")
            False
        """
        return bool(E164_REGEX.match(number))

    @staticmethod
    def import_dids(
        db: Session,
        dids: List[DIDImportItem],
        actor_id: UUID,
        source_ip: str,
        user_agent: str
    ) -> Tuple[int, List[DIDImportError]]:
        """
        Import multiple DIDs into the global pool (UNASSIGNED status).

        Validates all DIDs before import. If any validation fails, the entire
        transaction is rolled back (all-or-nothing).

        Args:
            db: Database session
            dids: List of DIDs to import
            actor_id: UUID of user performing the import
            source_ip: IP address of the request
            user_agent: User agent string from request

        Returns:
            Tuple of (number_imported, list_of_errors)

        Raises:
            RuntimeError: If database operation fails

        Validation Rules:
            - Must be valid E.164 format
            - Must not already exist in database
            - Maximum 10,000 DIDs per import
        """
        errors: List[DIDImportError] = []

        try:
            # Step 1: Validate E.164 format for all DIDs
            for did_item in dids:
                if not DIDService.validate_e164(did_item.number):
                    errors.append(DIDImportError(
                        number=did_item.number,
                        error="Invalid E.164 format"
                    ))

            # Step 2: Check for duplicates in database
            numbers = [did.number for did in dids]
            existing_numbers = db.query(PhoneNumber.number).filter(
                PhoneNumber.number.in_(numbers)
            ).all()
            existing_set = {num[0] for num in existing_numbers}

            for did_item in dids:
                if did_item.number in existing_set:
                    errors.append(DIDImportError(
                        number=did_item.number,
                        error="Duplicate number already exists"
                    ))

            # If any validation errors, rollback and return
            if errors:
                return (0, errors)

            # Step 3: Create PhoneNumber records with UNASSIGNED status
            created_count = 0
            for did_item in dids:
                phone_number = PhoneNumber(
                    number=did_item.number,
                    status=PhoneNumberStatus.UNASSIGNED,
                    tenant_id=None,  # UNASSIGNED means no tenant
                    provider=did_item.provider,
                    provider_metadata=did_item.provider_metadata or {}
                )
                db.add(phone_number)
                created_count += 1

            # Flush to get IDs before audit logging
            db.flush()

            # Step 4: Audit logging (use special UUID for bulk operations)
            from uuid import uuid4
            bulk_operation_id = uuid4()
            AuditService.log_create(
                session=db,
                entity_type="phone_number",
                entity_id=bulk_operation_id,  # Bulk operation uses generated UUID
                actor_id=actor_id,
                source_ip=source_ip,
                user_agent=user_agent,
                after_state={
                    "count": created_count,
                    "numbers": numbers[:100]  # Log first 100 for reference
                }
            )

            # Commit transaction
            db.commit()

            return (created_count, [])

        except IntegrityError as e:
            db.rollback()
            raise RuntimeError(f"Database integrity error during DID import: {str(e)}")
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Unexpected error during DID import: {str(e)}")

    @staticmethod
    def allocate_to_tenant(
        db: Session,
        phone_number_id: UUID,
        tenant_id: UUID,
        actor_id: UUID,
        source_ip: str,
        user_agent: str
    ) -> PhoneNumber:
        """
        Allocate an UNASSIGNED phone number to a tenant (status: UNASSIGNED → ALLOCATED).

        Args:
            db: Database session
            phone_number_id: UUID of phone number to allocate
            tenant_id: UUID of tenant to allocate to
            actor_id: UUID of user performing the allocation
            source_ip: IP address of the request
            user_agent: User agent string from request

        Returns:
            Updated PhoneNumber instance

        Raises:
            ValueError: If phone number not found or not in UNASSIGNED status
            RuntimeError: If database operation fails
        """
        # Fetch phone number
        phone_number = db.query(PhoneNumber).filter(
            PhoneNumber.id == phone_number_id
        ).first()

        if not phone_number:
            raise ValueError(f"Phone number not found: {phone_number_id}")

        if phone_number.status != PhoneNumberStatus.UNASSIGNED:
            raise ValueError(
                f"Phone number {phone_number.number} is {phone_number.status.value}, "
                f"expected UNASSIGNED"
            )

        # Capture before state for audit
        before_state = AuditService.entity_to_dict(phone_number)

        # Update status and tenant
        phone_number.status = PhoneNumberStatus.ALLOCATED
        phone_number.tenant_id = tenant_id

        # Capture after state for audit
        after_state = AuditService.entity_to_dict(phone_number)

        # Audit logging
        AuditService.log_update(
            session=db,
            entity_type="phone_number",
            entity_id=phone_number_id,
            actor_id=actor_id,
            source_ip=source_ip,
            user_agent=user_agent,
            before_state=before_state,
            after_state=after_state,
        )

        db.commit()
        return phone_number

    @staticmethod
    def deallocate(
        db: Session,
        phone_number_id: UUID,
        actor_id: UUID,
        source_ip: str,
        user_agent: str
    ) -> PhoneNumber:
        """
        Deallocate a phone number from a tenant (status: ALLOCATED → UNASSIGNED).

        Cannot deallocate ASSIGNED numbers - must unassign first.

        Args:
            db: Database session
            phone_number_id: UUID of phone number to deallocate
            actor_id: UUID of user performing the deallocation
            source_ip: IP address of the request
            user_agent: User agent string from request

        Returns:
            Updated PhoneNumber instance

        Raises:
            ValueError: If phone number not found, not ALLOCATED, or is ASSIGNED
            RuntimeError: If database operation fails
        """
        # Fetch phone number
        phone_number = db.query(PhoneNumber).filter(
            PhoneNumber.id == phone_number_id
        ).first()

        if not phone_number:
            raise ValueError(f"Phone number not found: {phone_number_id}")

        if phone_number.status == PhoneNumberStatus.ASSIGNED:
            raise ValueError(
                f"Cannot deallocate ASSIGNED phone number {phone_number.number}. "
                f"Unassign first."
            )

        if phone_number.status != PhoneNumberStatus.ALLOCATED:
            raise ValueError(
                f"Phone number {phone_number.number} is {phone_number.status.value}, "
                f"expected ALLOCATED"
            )

        # Capture before state for audit
        before_state = AuditService.entity_to_dict(phone_number)

        # Update status and clear tenant
        phone_number.status = PhoneNumberStatus.UNASSIGNED
        phone_number.tenant_id = None

        # Capture after state for audit
        after_state = AuditService.entity_to_dict(phone_number)

        # Audit logging
        AuditService.log_update(
            session=db,
            entity_type="phone_number",
            entity_id=phone_number_id,
            actor_id=actor_id,
            source_ip=source_ip,
            user_agent=user_agent,
            before_state=before_state,
            after_state=after_state,
        )

        db.commit()
        return phone_number

    @staticmethod
    def assign_to_destination(
        db: Session,
        phone_number_id: UUID,
        assigned_type: AssignmentType,
        assigned_id: Optional[UUID],
        assigned_value: Optional[str],
        actor_id: UUID,
        source_ip: str,
        user_agent: str
    ) -> DIDAssignment:
        """
        Assign an ALLOCATED phone number to a destination (status: ALLOCATED → ASSIGNED).

        Args:
            db: Database session
            phone_number_id: UUID of phone number to assign
            assigned_type: Type of destination (USER, IVR, QUEUE, EXTERNAL)
            assigned_id: UUID of destination entity (for USER, IVR, QUEUE)
            assigned_value: Dialplan context (for EXTERNAL)
            actor_id: UUID of user performing the assignment
            source_ip: IP address of the request
            user_agent: User agent string from request

        Returns:
            Created DIDAssignment instance

        Raises:
            ValueError: If validation fails (status, tenant mismatch, user not found)
            IntegrityError: If DID already assigned (unique constraint violation)
            RuntimeError: If database operation fails

        Validation Rules:
            - Phone number must exist and be ALLOCATED
            - For USER type: assigned_id required, user must exist and belong to same tenant
            - For EXTERNAL type: assigned_value required
            - Creates DIDAssignment and updates PhoneNumber status to ASSIGNED
        """
        from src.models.user import User

        # Fetch phone number
        phone_number = db.query(PhoneNumber).filter(
            PhoneNumber.id == phone_number_id
        ).first()

        if not phone_number:
            raise ValueError(f"Phone number not found: {phone_number_id}")

        if phone_number.status != PhoneNumberStatus.ALLOCATED:
            raise ValueError(
                f"Phone number {phone_number.number} is {phone_number.status.value}, "
                f"expected ALLOCATED"
            )

        # Validate assignment type and fields
        if assigned_type in [AssignmentType.USER, AssignmentType.IVR, AssignmentType.QUEUE]:
            if not assigned_id:
                raise ValueError(f"assigned_id is required for {assigned_type.value}")
            if assigned_value:
                raise ValueError(f"assigned_value must be null for {assigned_type.value}")

            # For USER type, validate user exists and belongs to same tenant
            if assigned_type == AssignmentType.USER:
                user = db.query(User).filter(User.id == assigned_id).first()
                if not user:
                    raise ValueError(f"User not found: {assigned_id}")
                if user.tenant_id != phone_number.tenant_id:
                    raise ValueError(
                        f"User belongs to different tenant. "
                        f"Phone number tenant: {phone_number.tenant_id}, "
                        f"User tenant: {user.tenant_id}"
                    )

        elif assigned_type == AssignmentType.EXTERNAL:
            if not assigned_value:
                raise ValueError("assigned_value is required for EXTERNAL")
            if assigned_id:
                raise ValueError("assigned_id must be null for EXTERNAL")
        else:
            raise ValueError(f"Invalid assignment type: {assigned_type}")

        try:
            # Create DIDAssignment
            assignment = DIDAssignment(
                phone_number_id=phone_number_id,
                assigned_type=assigned_type,
                assigned_id=assigned_id,
                assigned_value=assigned_value,
                created_by=actor_id
            )
            db.add(assignment)

            # Update PhoneNumber status to ASSIGNED
            phone_number.status = PhoneNumberStatus.ASSIGNED

            # Flush to get assignment ID before audit logging
            db.flush()

            # Audit logging
            AuditService.log_create(
                session=db,
                entity_type="did_assignment",
                entity_id=assignment.id,
                actor_id=actor_id,
                source_ip=source_ip,
                user_agent=user_agent,
                after_state={
                    "phone_number": phone_number.number,
                    "assigned_type": assigned_type.value,
                    "assigned_id": str(assigned_id) if assigned_id else None,
                    "assigned_value": assigned_value
                }
            )

            db.commit()
            return assignment

        except IntegrityError as e:
            db.rollback()
            if "uq_did_assignments_phone_number_id" in str(e):
                raise IntegrityError(
                    f"Phone number {phone_number.number} is already assigned",
                    params=None,
                    orig=e.orig
                )
            raise RuntimeError(f"Database integrity error during assignment: {str(e)}")
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Unexpected error during assignment: {str(e)}")

    @staticmethod
    def unassign(
        db: Session,
        phone_number_id: UUID,
        actor_id: UUID,
        source_ip: str,
        user_agent: str
    ) -> PhoneNumber:
        """
        Unassign a phone number from its destination (status: ASSIGNED → ALLOCATED).

        Deletes the DIDAssignment and returns phone number to ALLOCATED status.

        Args:
            db: Database session
            phone_number_id: UUID of phone number to unassign
            actor_id: UUID of user performing the unassignment
            source_ip: IP address of the request
            user_agent: User agent string from request

        Returns:
            Updated PhoneNumber instance

        Raises:
            ValueError: If phone number not found or not ASSIGNED
            RuntimeError: If database operation fails
        """
        # Fetch phone number with assignment
        phone_number = db.query(PhoneNumber).filter(
            PhoneNumber.id == phone_number_id
        ).first()

        if not phone_number:
            raise ValueError(f"Phone number not found: {phone_number_id}")

        if phone_number.status != PhoneNumberStatus.ASSIGNED:
            raise ValueError(
                f"Phone number {phone_number.number} is {phone_number.status.value}, "
                f"expected ASSIGNED"
            )

        # Fetch and delete assignment
        assignment = db.query(DIDAssignment).filter(
            DIDAssignment.phone_number_id == phone_number_id
        ).first()

        if not assignment:
            raise ValueError(
                f"No assignment found for phone number {phone_number.number}"
            )

        # Capture assignment details for audit before deletion
        assignment_data = {
            "id": str(assignment.id),
            "assigned_type": assignment.assigned_type.value,
            "assigned_id": str(assignment.assigned_id) if assignment.assigned_id else None,
            "assigned_value": assignment.assigned_value
        }

        # Delete assignment
        db.delete(assignment)

        # Update phone number status back to ALLOCATED
        phone_number.status = PhoneNumberStatus.ALLOCATED

        # Audit logging
        AuditService.log_delete(
            session=db,
            entity_type="did_assignment",
            entity_id=assignment.id,
            actor_id=actor_id,
            source_ip=source_ip,
            user_agent=user_agent,
            metadata={
                "phone_number": phone_number.number,
                "previous_assignment": assignment_data
            }
        )

        db.commit()
        return phone_number
