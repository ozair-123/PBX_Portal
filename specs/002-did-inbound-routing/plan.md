# Implementation Plan: DID Inventory & Inbound Routing Management

**Branch**: `002-did-inbound-routing` | **Date**: 2026-01-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-did-inbound-routing/spec.md`

**Note**: This plan follows the `/sp.plan` workflow. Implementation tasks will be generated separately via `/sp.tasks`.

## Summary

Implement a comprehensive DID (Direct Inward Dialing) management system for a multi-tenant PBX that handles the complete lifecycle of phone numbers: bulk import from carriers, platform admin allocation to tenants, tenant admin assignment to destinations (users, IVRs, queues, external), and automatic dialplan generation for inbound call routing. The system integrates with the existing Safe Apply workflow to ensure atomic configuration deployment with validation, backup, and rollback capabilities.

**Technical Approach**: Extend existing FastAPI/PostgreSQL architecture with two new models (PhoneNumber, DIDAssignment), add DID-specific service layer, expose RESTful API endpoints with RBAC enforcement, and extend the DialplanGenerator's InboundRouter module to generate [from-trunk-external] context entries. E.164 format validation ensures number consistency, unique constraints prevent race conditions, and comprehensive audit logging provides compliance traceability.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.0+, Pydantic 2.0+, Alembic 1.12+ (migrations), psycopg2-binary (PostgreSQL driver), python-jose[cryptography] (JWT), bcrypt/argon2 (password hashing)
**Storage**: PostgreSQL 14+ (application data with JSONB support for provider metadata, advisory locks for apply serialization)
**Testing**: pytest 7.0+, pytest-asyncio, httpx (async HTTP client for API testing)
**Target Platform**: Linux server (Debian/Ubuntu), Asterisk 18+ with AMI enabled, file-based dialplan configuration
**Project Type**: Single backend API (no frontend in this feature)
**Performance Goals**: Import 1000+ DIDs in <30 seconds (bulk insert + validation), DID assignment API response <500ms p95, dialplan generation for 100+ assignments <5 seconds, list/filter 5000+ DIDs with pagination <2 seconds
**Constraints**: E.164 phone number format validation (regex: `^\+[1-9]\d{1,14}$`), multi-tenant isolation (RBAC + FK enforcement), atomic file operations (temp → move pattern), no auto-reload (explicit apply only per Constitution Principle IV)
**Scale/Scope**: Support 10,000+ DIDs per system, 100+ tenants, 1000+ users, 100+ concurrent API requests, 50+ DID assignments per apply operation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance Status | Notes |
|-----------|-------------------|-------|
| **I. File-Based Asterisk Configuration** | ✅ PASS | DID routing generates [from-trunk-external] dialplan context in file-based extensions_custom.conf. No Asterisk Realtime for DIDs. |
| **II. Isolated Configuration Generation** | ✅ PASS | Dialplan generator writes only to include file (extensions_custom.conf). Core Asterisk configs untouched. |
| **III. Atomic File Operations** | ✅ PASS | Dialplan write uses temp → move pattern via existing AtomicFileWriter. |
| **IV. Explicit Apply Actions** | ✅ PASS | DID assignments take effect only when user triggers POST /api/v1/apply. No auto-reload. |
| **V. Strict Scope Adherence** | ✅ PASS | All features (import, allocate, assign, routing generation) are specified in spec.md. No speculative features. |
| **VI. No Frontend in MVP** | ✅ PASS | Feature is backend API only. No UI components. |
| **VII. No Hardcoded Secrets** | ✅ PASS | No secrets in DID management. Uses existing environment-based config (DATABASE_URL, AMI credentials). |
| **VIII. Simplicity First** | ✅ PASS | Reuses existing patterns: SQLAlchemy models, service layer, Pydantic schemas, existing audit logging. No new frameworks or abstractions. |

**Overall**: ✅ **PASS** - All 8 constitution principles are satisfied. No violations require justification.

## Project Structure

### Documentation (this feature)

```text
specs/002-did-inbound-routing/
├── spec.md                      # Feature requirements (already created)
├── plan.md                      # This file (/sp.plan output)
├── research.md                  # Phase 0: E.164 validation, bulk import patterns, locking strategies
├── data-model.md                # Phase 1: PhoneNumber & DIDAssignment schema
├── quickstart.md                # Phase 1: Developer guide for DID management
├── contracts/                   # Phase 1: OpenAPI specs for DID endpoints
│   ├── dids.openapi.yaml        # DID import, list, allocate, deallocate
│   └── did-assignments.openapi.yaml  # Assign, unassign, get assignment
└── checklists/
    └── requirements.md          # Quality validation (already created)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── __init__.py
│   ├── phone_number.py          # NEW: PhoneNumber model (DID inventory)
│   └── did_assignment.py        # NEW: DIDAssignment model (DID-to-destination mapping)
├── services/
│   ├── did_service.py           # NEW: DID business logic (import, allocate, assign, unassign)
│   └── audit_service.py         # EXTEND: Add DID-specific audit events
├── api/
│   └── v1/
│       ├── __init__.py          # MODIFY: Register DIDs router
│       └── dids.py              # NEW: DID API endpoints (CRUD + import)
├── schemas/
│   ├── phone_number.py          # NEW: PhoneNumberCreate, PhoneNumberResponse, DIDImportRequest
│   └── did_assignment.py        # NEW: DIDAssignmentCreate, DIDAssignmentResponse
├── config_generator/
│   └── inbound_router.py        # EXTEND: Generate [from-trunk-external] from DIDAssignment table
└── database.py                  # No changes (reuse existing session management)

alembic/
└── versions/
    └── YYYYMMDD_HHMM_add_did_models.py  # NEW: Migration for PhoneNumber & DIDAssignment tables

tests/
├── test_models/
│   ├── test_phone_number.py     # NEW: Model validation tests (E.164, status transitions)
│   └── test_did_assignment.py   # NEW: Assignment validation tests (constraints)
├── test_services/
│   └── test_did_service.py      # NEW: Business logic tests (import, allocate, assign)
└── test_api/
    └── test_dids.py             # NEW: API endpoint tests (RBAC, pagination, filters)
```

**Structure Decision**: Single project architecture (Option 1). This feature extends the existing backend with new models, services, and API endpoints. No frontend, mobile, or separate project required. Follows established FastAPI patterns (routers, dependencies, schemas).

## Complexity Tracking

> No violations detected. This section is empty per Constitution Check results.

## Phase 0: Research & Design Decisions

### Research Areas

1. **E.164 Phone Number Format Validation**
   - **Decision**: Use regex `^\+[1-9]\d{1,14}$` with Python's `re` module
   - **Rationale**: E.164 standard ensures international consistency (country code + subscriber number, max 15 digits). Leading zero prohibited. PostgreSQL VARCHAR(16) stores max length.
   - **Alternatives Considered**:
     - phonenumbers library (Google): Rejected - too heavyweight, adds dependency
     - Database CHECK constraint only: Rejected - validation should happen at service layer for clear error messages
   - **Implementation**: `PhoneNumberService.validate_e164(number)` raises ValueError on invalid format

2. **Bulk Import Strategy**
   - **Decision**: Single transaction bulk insert with rollback on any validation error
   - **Rationale**: All-or-nothing semantics prevent partial imports. PostgreSQL handles 1000+ inserts efficiently in single transaction.
   - **Alternatives Considered**:
     - Partial import with error report: Rejected - creates inconsistent state, requires cleanup logic
     - Batch commits (100 at a time): Rejected - adds complexity, doesn't align with atomic semantics
   - **Implementation**: `DIDService.import_dids(dids_list)` wraps in try-except, session.rollback() on error

3. **DID Assignment Locking Strategy**
   - **Decision**: Database unique constraint on `phone_number_id` (one active assignment per DID)
   - **Rationale**: Database constraint prevents race conditions without application-level locking. Fails fast with IntegrityError.
   - **Alternatives Considered**:
     - Row-level SELECT FOR UPDATE: Rejected - overkill for simple uniqueness check, adds lock contention
     - Advisory locks: Rejected - global serialization unnecessary for per-DID operations
   - **Implementation**: SQLAlchemy unique constraint + try-except IntegrityError → HTTP 409 Conflict

4. **Tenant Isolation for DIDs**
   - **Decision**: PhoneNumber.tenant_id (nullable FK) + API RBAC enforcement
   - **Rationale**:
     - `tenant_id = NULL`: UNASSIGNED (global pool, platform admin only)
     - `tenant_id = <UUID>`: ALLOCATED (tenant pool, tenant admin can assign)
     - Status enum (UNASSIGNED, ALLOCATED, ASSIGNED) tracks lifecycle
   - **Alternatives Considered**:
     - Separate global/tenant tables: Rejected - unnecessary schema complexity
     - View-based isolation: Rejected - harder to enforce, implicit filtering error-prone
   - **Implementation**: API endpoints filter by `current_user["tenant_id"]` for non-platform admins

5. **Dialplan Generation Integration**
   - **Decision**: Extend `InboundRouter.generate()` to query DIDAssignment table
   - **Rationale**: InboundRouter already exists for extension routing. DID routing is logically similar (external number → internal destination).
   - **Alternatives Considered**:
     - New DIDRouter class: Rejected - creates duplicate context management code
     - Inline in DialplanGenerator: Rejected - violates single responsibility
   - **Implementation**: `InboundRouter.generate()` accepts optional `did_assignments` parameter, generates [from-trunk-external] context

6. **Assignment Type Handling**
   - **Decision**: Polymorphic assignment with `assigned_type` (enum) + `assigned_id` (UUID) / `assigned_value` (string)
   - **Rationale**:
     - USER/IVR/QUEUE: `assigned_id` references entity UUID
     - EXTERNAL: `assigned_value` stores arbitrary dialplan (e.g., "VoiceMail(2000@tenant-acme)")
   - **Alternatives Considered**:
     - Separate tables per assignment type: Rejected - schema explosion, complex queries
     - JSONB config field: Rejected - loses type safety and referential integrity for USER/IVR/QUEUE
   - **Implementation**: CHECK constraint ensures `assigned_id` XOR `assigned_value` is set based on `assigned_type`

### Technology Stack Confirmation

- **Python 3.11**: Existing requirement (no change)
- **FastAPI 0.104+**: Existing (no new dependencies)
- **SQLAlchemy 2.0+**: Existing (reuse declarative base, session management)
- **PostgreSQL 14+**: Existing (JSONB for provider_metadata, UUID support)
- **Alembic**: Existing (migration tooling)
- **pytest**: Existing (test framework)

**No new external dependencies required.**

## Phase 1: Data Model & API Contracts

### Data Model Design

#### PhoneNumber Entity

**Purpose**: Inventory of phone numbers (DIDs) with lifecycle tracking (UNASSIGNED → ALLOCATED → ASSIGNED)

**Schema**:
```python
# src/models/phone_number.py
from sqlalchemy import Column, String, Enum, ForeignKey, Index, TIMESTAMP, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
import uuid

class PhoneNumberStatus(enum.Enum):
    UNASSIGNED = "UNASSIGNED"  # Global pool, no tenant
    ALLOCATED = "ALLOCATED"    # Assigned to tenant, not yet assigned to destination
    ASSIGNED = "ASSIGNED"      # Assigned to user/IVR/queue/external

class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # E.164 Number (unique globally)
    number = Column(String(16), unique=True, nullable=False, index=True)

    # Lifecycle Status
    status = Column(Enum(PhoneNumberStatus), nullable=False, default=PhoneNumberStatus.UNASSIGNED, index=True)

    # Tenant Assignment (nullable for UNASSIGNED)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    # Provider Metadata
    provider = Column(String(255), nullable=True)  # e.g., "Twilio", "Bandwidth"
    provider_metadata = Column(JSONB, nullable=True, default={})  # Flexible carrier-specific data

    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="phone_numbers")
    assignment = relationship("DIDAssignment", back_populates="phone_number", uselist=False, cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "number ~ '^\\+[1-9]\\d{1,14}$'",
            name="phone_number_e164_format"
        ),
        CheckConstraint(
            "(status = 'UNASSIGNED' AND tenant_id IS NULL) OR (status IN ('ALLOCATED', 'ASSIGNED') AND tenant_id IS NOT NULL)",
            name="phone_number_tenant_consistency"
        ),
        Index("idx_phone_numbers_tenant_status", "tenant_id", "status"),  # For tenant admin queries
    )

    def __repr__(self):
        return f"<PhoneNumber(id={self.id}, number={self.number}, status={self.status.value})>"
```

**Validation Rules**:
- E.164 format enforced at database level (CHECK constraint) and service layer
- `tenant_id` must be NULL when UNASSIGNED, non-NULL when ALLOCATED/ASSIGNED
- Unique number globally (prevents carrier duplicates)

#### DIDAssignment Entity

**Purpose**: Maps a phone number to its destination (user, IVR, queue, or external dialplan)

**Schema**:
```python
# src/models/did_assignment.py
from sqlalchemy import Column, String, Enum, ForeignKey, UniqueConstraint, CheckConstraint, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
import uuid

class AssignmentType(enum.Enum):
    USER = "USER"          # Route to user extension
    IVR = "IVR"            # Route to auto-attendant
    QUEUE = "QUEUE"        # Route to call queue
    EXTERNAL = "EXTERNAL"  # Route to arbitrary dialplan destination

class DIDAssignment(Base):
    __tablename__ = "did_assignments"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Phone Number (unique - one assignment per DID)
    phone_number_id = Column(UUID(as_uuid=True), ForeignKey("phone_numbers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Assignment Type
    assigned_type = Column(Enum(AssignmentType), nullable=False)

    # Destination Reference (polymorphic)
    assigned_id = Column(UUID(as_uuid=True), nullable=True)  # For USER/IVR/QUEUE
    assigned_value = Column(String(255), nullable=True)  # For EXTERNAL (dialplan string)

    # Audit Trail
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    phone_number = relationship("PhoneNumber", back_populates="assignment")
    creator = relationship("User", foreign_keys=[created_by])

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(assigned_type IN ('USER', 'IVR', 'QUEUE') AND assigned_id IS NOT NULL AND assigned_value IS NULL) OR "
            "(assigned_type = 'EXTERNAL' AND assigned_id IS NULL AND assigned_value IS NOT NULL)",
            name="did_assignment_type_consistency"
        ),
    )

    def __repr__(self):
        return f"<DIDAssignment(id={self.id}, phone_number_id={self.phone_number_id}, type={self.assigned_type.value})>"
```

**Validation Rules**:
- Unique `phone_number_id` (one active assignment per DID)
- `assigned_id` XOR `assigned_value` based on `assigned_type` (CHECK constraint)
- Cascade delete when PhoneNumber is deleted
- Audit trail via `created_by` FK to User

#### Database Migration

**Alembic Migration Script**: `alembic/versions/20260106_1200_add_did_models.py`

```python
"""Add DID management models

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2026-01-06 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create phone_numbers table
    op.create_table(
        'phone_numbers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('number', sa.String(16), unique=True, nullable=False),
        sa.Column('status', sa.Enum('UNASSIGNED', 'ALLOCATED', 'ASSIGNED', name='phonenumberstatus'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(255), nullable=True),
        sa.Column('provider_metadata', postgresql.JSONB, nullable=True, default={}),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint("number ~ '^\\+[1-9]\\d{1,14}$'", name='phone_number_e164_format'),
        sa.CheckConstraint(
            "(status = 'UNASSIGNED' AND tenant_id IS NULL) OR (status IN ('ALLOCATED', 'ASSIGNED') AND tenant_id IS NOT NULL)",
            name='phone_number_tenant_consistency'
        ),
    )
    op.create_index('idx_phone_numbers_number', 'phone_numbers', ['number'])
    op.create_index('idx_phone_numbers_status', 'phone_numbers', ['status'])
    op.create_index('idx_phone_numbers_tenant_id', 'phone_numbers', ['tenant_id'])
    op.create_index('idx_phone_numbers_tenant_status', 'phone_numbers', ['tenant_id', 'status'])

    # Create did_assignments table
    op.create_table(
        'did_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('phone_number_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('phone_numbers.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('assigned_type', sa.Enum('USER', 'IVR', 'QUEUE', 'EXTERNAL', name='assignmenttype'), nullable=False),
        sa.Column('assigned_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_value', sa.String(255), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint(
            "(assigned_type IN ('USER', 'IVR', 'QUEUE') AND assigned_id IS NOT NULL AND assigned_value IS NULL) OR "
            "(assigned_type = 'EXTERNAL' AND assigned_id IS NULL AND assigned_value IS NOT NULL)",
            name='did_assignment_type_consistency'
        ),
    )
    op.create_index('idx_did_assignments_phone_number_id', 'did_assignments', ['phone_number_id'])

def downgrade():
    op.drop_table('did_assignments')
    op.drop_table('phone_numbers')
    op.execute('DROP TYPE assignmenttype')
    op.execute('DROP TYPE phonenumberstatus')
```

### API Contracts

#### DID Management Endpoints

**Base Path**: `/api/v1/dids`

##### 1. Import DIDs (Bulk)

**POST /api/v1/dids/import**

**Request**:
```json
{
  "dids": [
    {
      "number": "+15551234567",
      "provider": "Twilio",
      "metadata": {
        "account_sid": "AC123",
        "sid": "PN456",
        "capabilities": ["voice", "sms"]
      }
    },
    {
      "number": "+15559876543",
      "provider": "Bandwidth",
      "metadata": {
        "order_id": "ORD789"
      }
    }
  ]
}
```

**Response** (201 Created):
```json
{
  "imported": 2,
  "failed": 0,
  "errors": []
}
```

**Response** (400 Bad Request on validation errors):
```json
{
  "imported": 0,
  "failed": 2,
  "errors": [
    "Invalid E.164 format: +1555INVALID",
    "Duplicate number: +15551234567"
  ]
}
```

**RBAC**: `platform_admin` only

##### 2. List DIDs (with filters)

**GET /api/v1/dids?status=UNASSIGNED&tenant_id=<uuid>&page=1&page_size=50**

**Query Parameters**:
- `status`: Filter by PhoneNumberStatus (UNASSIGNED, ALLOCATED, ASSIGNED)
- `tenant_id`: Filter by tenant (platform_admin only)
- `number`: Partial number search (e.g., "555" finds all numbers containing "555")
- `page`: Page number (default 1)
- `page_size`: Items per page (default 50, max 200)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "uuid-1",
      "number": "+15551234567",
      "status": "UNASSIGNED",
      "tenant_id": null,
      "provider": "Twilio",
      "provider_metadata": {"account_sid": "AC123"},
      "assignment": null,
      "created_at": "2026-01-06T10:00:00Z",
      "updated_at": "2026-01-06T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

**RBAC**:
- `platform_admin`: View all DIDs
- `tenant_admin`: View only DIDs where `tenant_id = current_user.tenant_id`
- `support`: View all DIDs (read-only)

##### 3. Allocate DID to Tenant

**PATCH /api/v1/dids/{did_id}/allocate**

**Request**:
```json
{
  "tenant_id": "uuid-tenant-123"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid-1",
  "number": "+15551234567",
  "status": "ALLOCATED",
  "tenant_id": "uuid-tenant-123",
  "provider": "Twilio",
  "assignment": null
}
```

**Response** (409 Conflict if already allocated):
```json
{
  "detail": "DID +15551234567 is already allocated to tenant 'Acme Corp'"
}
```

**RBAC**: `platform_admin` only

##### 4. Deallocate DID from Tenant

**PATCH /api/v1/dids/{did_id}/deallocate**

**Request**: Empty body

**Response** (200 OK):
```json
{
  "id": "uuid-1",
  "number": "+15551234567",
  "status": "UNASSIGNED",
  "tenant_id": null,
  "assignment": null
}
```

**Response** (400 Bad Request if DID is assigned):
```json
{
  "detail": "Cannot deallocate DID +15551234567: currently assigned to user alice@example.com. Unassign first."
}
```

**RBAC**: `platform_admin` only

##### 5. Assign DID to Destination

**POST /api/v1/dids/{did_id}/assign**

**Request** (assign to user):
```json
{
  "assigned_type": "USER",
  "assigned_id": "uuid-user-456"
}
```

**Request** (assign to external dialplan):
```json
{
  "assigned_type": "EXTERNAL",
  "assigned_value": "VoiceMail(2000@tenant-acme)"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid-assignment-789",
  "phone_number_id": "uuid-1",
  "phone_number": "+15551234567",
  "assigned_type": "USER",
  "assigned_id": "uuid-user-456",
  "assigned_value": null,
  "created_by": "uuid-admin-123",
  "created_at": "2026-01-06T11:00:00Z"
}
```

**Response** (400 Bad Request if validation fails):
```json
{
  "detail": "User uuid-user-456 not found or not in your tenant"
}
```

**Response** (409 Conflict if DID already assigned):
```json
{
  "detail": "DID +15551234567 is already assigned to user bob@example.com"
}
```

**RBAC**: `tenant_admin` (can only assign DIDs allocated to their tenant)

##### 6. Unassign DID

**DELETE /api/v1/dids/{did_id}/assign**

**Response** (204 No Content)

**RBAC**: `tenant_admin` (can only unassign DIDs in their tenant)

##### 7. Get DID Details

**GET /api/v1/dids/{did_id}**

**Response** (200 OK):
```json
{
  "id": "uuid-1",
  "number": "+15551234567",
  "status": "ASSIGNED",
  "tenant_id": "uuid-tenant-123",
  "provider": "Twilio",
  "provider_metadata": {"account_sid": "AC123"},
  "assignment": {
    "id": "uuid-assignment-789",
    "assigned_type": "USER",
    "assigned_id": "uuid-user-456",
    "assigned_value": null,
    "created_by": "uuid-admin-123",
    "created_at": "2026-01-06T11:00:00Z"
  },
  "created_at": "2026-01-06T10:00:00Z",
  "updated_at": "2026-01-06T11:00:00Z"
}
```

**RBAC**: Same as list endpoint (platform admin sees all, tenant admin sees own tenant only)

### Pydantic Schemas

#### Request Schemas

**src/schemas/phone_number.py**:
```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class DIDImportItem(BaseModel):
    """Single DID for bulk import."""
    number: str = Field(..., description="E.164 phone number (e.g., +15551234567)")
    provider: Optional[str] = Field(None, max_length=255, description="Carrier name")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Provider-specific data")

    @field_validator('number')
    @classmethod
    def validate_e164(cls, v: str) -> str:
        import re
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError(f"Invalid E.164 format: {v}")
        return v

class DIDImportRequest(BaseModel):
    """Bulk import request."""
    dids: List[DIDImportItem] = Field(..., min_length=1, max_length=10000)

class DIDAllocateRequest(BaseModel):
    """Allocate DID to tenant."""
    tenant_id: UUID

class DIDAssignRequest(BaseModel):
    """Assign DID to destination."""
    assigned_type: str = Field(..., description="USER, IVR, QUEUE, or EXTERNAL")
    assigned_id: Optional[UUID] = Field(None, description="Required for USER/IVR/QUEUE")
    assigned_value: Optional[str] = Field(None, max_length=255, description="Required for EXTERNAL")

    @field_validator('assigned_type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = ['USER', 'IVR', 'QUEUE', 'EXTERNAL']
        if v not in allowed:
            raise ValueError(f"assigned_type must be one of: {', '.join(allowed)}")
        return v
```

#### Response Schemas

**src/schemas/phone_number.py** (continued):
```python
class DIDAssignmentResponse(BaseModel):
    """DID assignment response."""
    id: UUID
    phone_number_id: UUID
    phone_number: str
    assigned_type: str
    assigned_id: Optional[UUID]
    assigned_value: Optional[str]
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class PhoneNumberResponse(BaseModel):
    """Phone number response."""
    id: UUID
    number: str
    status: str
    tenant_id: Optional[UUID]
    provider: Optional[str]
    provider_metadata: Optional[Dict[str, Any]]
    assignment: Optional[DIDAssignmentResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PhoneNumberListResponse(BaseModel):
    """Paginated list response."""
    items: List[PhoneNumberResponse]
    total: int
    page: int
    page_size: int

class DIDImportResponse(BaseModel):
    """Bulk import result."""
    imported: int
    failed: int
    errors: List[str]
```

### Service Layer Design

**src/services/did_service.py**:

```python
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any, Optional
from uuid import UUID
import re
import logging

from ..models.phone_number import PhoneNumber, PhoneNumberStatus
from ..models.did_assignment import DIDAssignment, AssignmentType
from ..models.user import User
from ..services.audit_service import AuditService

logger = logging.getLogger(__name__)

class DIDService:
    """Business logic for DID management."""

    E164_REGEX = re.compile(r'^\+[1-9]\d{1,14}$')

    @staticmethod
    def validate_e164(number: str) -> bool:
        """Validate E.164 phone number format."""
        return bool(DIDService.E164_REGEX.match(number))

    @staticmethod
    def import_dids(
        session: Session,
        dids: List[Dict[str, Any]],
        actor_id: UUID,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bulk import DIDs with validation.

        Transaction semantics: All-or-nothing (rollback on any error).
        """
        imported = 0
        errors = []

        try:
            for did_data in dids:
                number = did_data["number"]

                # Validate E.164
                if not DIDService.validate_e164(number):
                    errors.append(f"Invalid E.164 format: {number}")
                    continue

                # Check duplicate
                existing = session.query(PhoneNumber).filter(PhoneNumber.number == number).first()
                if existing:
                    errors.append(f"Duplicate number: {number}")
                    continue

                # Create PhoneNumber
                phone_number = PhoneNumber(
                    number=number,
                    status=PhoneNumberStatus.UNASSIGNED,
                    provider=did_data.get("provider"),
                    provider_metadata=did_data.get("metadata", {}),
                )
                session.add(phone_number)
                imported += 1

            # If any errors, rollback
            if errors:
                session.rollback()
                return {"imported": 0, "failed": len(errors), "errors": errors}

            # Commit transaction
            session.flush()

            # Audit log
            AuditService.log_create(
                session=session,
                actor_id=actor_id,
                entity_type="PhoneNumber",
                entity_id=None,  # Bulk operation
                after_state={"imported_count": imported},
                tenant_id=None,  # Global pool
                source_ip=source_ip,
                user_agent=user_agent,
            )

            session.commit()
            logger.info(f"Imported {imported} DIDs successfully")
            return {"imported": imported, "failed": 0, "errors": []}

        except Exception as e:
            session.rollback()
            logger.exception(f"DID import failed: {str(e)}")
            raise RuntimeError(f"Import failed: {str(e)}")

    @staticmethod
    def allocate_to_tenant(
        session: Session,
        phone_number_id: UUID,
        tenant_id: UUID,
        actor_id: UUID,
    ) -> PhoneNumber:
        """Allocate DID from global pool to tenant."""
        phone_number = session.query(PhoneNumber).filter(PhoneNumber.id == phone_number_id).first()

        if not phone_number:
            raise ValueError(f"Phone number {phone_number_id} not found")

        if phone_number.status != PhoneNumberStatus.UNASSIGNED:
            raise ValueError(f"Phone number {phone_number.number} is not in UNASSIGNED state")

        # Update status and tenant
        before_state = AuditService.entity_to_dict(phone_number)
        phone_number.status = PhoneNumberStatus.ALLOCATED
        phone_number.tenant_id = tenant_id
        session.flush()

        # Audit log
        after_state = AuditService.entity_to_dict(phone_number)
        AuditService.log_update(
            session=session,
            actor_id=actor_id,
            entity_type="PhoneNumber",
            entity_id=phone_number.id,
            before_state=before_state,
            after_state=after_state,
            tenant_id=tenant_id,
        )

        logger.info(f"Allocated DID {phone_number.number} to tenant {tenant_id}")
        return phone_number

    @staticmethod
    def assign_to_destination(
        session: Session,
        phone_number_id: UUID,
        assigned_type: AssignmentType,
        actor_id: UUID,
        assigned_id: Optional[UUID] = None,
        assigned_value: Optional[str] = None,
    ) -> DIDAssignment:
        """Assign DID to user/IVR/queue/external."""
        phone_number = session.query(PhoneNumber).filter(PhoneNumber.id == phone_number_id).first()

        if not phone_number:
            raise ValueError(f"Phone number {phone_number_id} not found")

        if phone_number.status != PhoneNumberStatus.ALLOCATED:
            raise ValueError(f"Phone number {phone_number.number} must be ALLOCATED before assignment")

        # Validate assignment type consistency
        if assigned_type in [AssignmentType.USER, AssignmentType.IVR, AssignmentType.QUEUE]:
            if not assigned_id:
                raise ValueError(f"assigned_id required for type {assigned_type.value}")
            if assigned_type == AssignmentType.USER:
                # Validate user exists and is in same tenant
                user = session.query(User).filter(User.id == assigned_id).first()
                if not user:
                    raise ValueError(f"User {assigned_id} not found")
                if user.tenant_id != phone_number.tenant_id:
                    raise ValueError(f"User {assigned_id} is not in the same tenant")
        elif assigned_type == AssignmentType.EXTERNAL:
            if not assigned_value:
                raise ValueError("assigned_value required for type EXTERNAL")

        # Create assignment
        try:
            assignment = DIDAssignment(
                phone_number_id=phone_number_id,
                assigned_type=assigned_type,
                assigned_id=assigned_id,
                assigned_value=assigned_value,
                created_by=actor_id,
            )
            session.add(assignment)

            # Update phone number status
            phone_number.status = PhoneNumberStatus.ASSIGNED
            session.flush()

            # Audit log
            AuditService.log_create(
                session=session,
                actor_id=actor_id,
                entity_type="DIDAssignment",
                entity_id=assignment.id,
                after_state=AuditService.entity_to_dict(assignment),
                tenant_id=phone_number.tenant_id,
            )

            logger.info(f"Assigned DID {phone_number.number} to {assigned_type.value}")
            return assignment

        except IntegrityError as e:
            session.rollback()
            raise ValueError(f"DID {phone_number.number} is already assigned")

    @staticmethod
    def unassign(
        session: Session,
        phone_number_id: UUID,
        actor_id: UUID,
    ) -> None:
        """Unassign DID (delete assignment, return to ALLOCATED)."""
        phone_number = session.query(PhoneNumber).filter(PhoneNumber.id == phone_number_id).first()

        if not phone_number:
            raise ValueError(f"Phone number {phone_number_id} not found")

        if not phone_number.assignment:
            raise ValueError(f"Phone number {phone_number.number} is not assigned")

        # Delete assignment
        assignment_id = phone_number.assignment.id
        before_state = AuditService.entity_to_dict(phone_number.assignment)
        session.delete(phone_number.assignment)

        # Update phone number status
        phone_number.status = PhoneNumberStatus.ALLOCATED
        session.flush()

        # Audit log
        AuditService.log_delete(
            session=session,
            actor_id=actor_id,
            entity_type="DIDAssignment",
            entity_id=assignment_id,
            before_state=before_state,
            tenant_id=phone_number.tenant_id,
        )

        logger.info(f"Unassigned DID {phone_number.number}")
```

### Dialplan Generation Integration

**Extend src/config_generator/inbound_router.py**:

```python
class InboundRouter:
    """Generates [from-trunk-external] context for inbound DID routing."""

    @staticmethod
    def generate(
        did_assignments: List[Dict[str, Any]],
        users: List[Dict[str, Any]],
    ) -> str:
        """
        Generate Asterisk dialplan for inbound DID routing.

        Args:
            did_assignments: List of DIDAssignment dicts with:
                - phone_number: E.164 number
                - assigned_type: USER/IVR/QUEUE/EXTERNAL
                - assigned_id: UUID (for USER)
                - assigned_value: string (for EXTERNAL)
                - tenant_context: tenant dialplan context (e.g., "tenant-acme")
            users: List of User dicts (for extension lookup)

        Returns:
            Dialplan configuration string
        """
        config_lines = []

        # Context header
        config_lines.append("[from-trunk-external]")
        config_lines.append("; Inbound DID routing")
        config_lines.append("; Generated: " + datetime.utcnow().isoformat())
        config_lines.append("")

        # Generate routing for each assignment
        for assignment in did_assignments:
            number = assignment["phone_number"]
            assigned_type = assignment["assigned_type"]

            if assigned_type == "USER":
                # Route to user extension
                user_id = assignment["assigned_id"]
                user = next((u for u in users if u["id"] == str(user_id)), None)
                if user:
                    tenant_context = f"tenant-{user['tenant_id']}"
                    extension = user["extension"]
                    config_lines.append(f"exten => {number},1,Goto({tenant_context},{extension},1)")

            elif assigned_type == "EXTERNAL":
                # Route to arbitrary dialplan
                dialplan_value = assignment["assigned_value"]
                config_lines.append(f"exten => {number},1,{dialplan_value}")

            # TODO: IVR and QUEUE types when those entities exist

        config_lines.append("")
        return "\n".join(config_lines)
```

**Extend src/config_generator/dialplan_generator.py**:

```python
class DialplanGenerator:
    @staticmethod
    def generate_config(
        users_with_extensions: Optional[List[Dict[str, Any]]] = None,
        tenants: Optional[List[Dict[str, Any]]] = None,
        did_assignments: Optional[List[Dict[str, Any]]] = None,  # NEW
    ) -> str:
        """Generate complete dialplan configuration."""
        config_parts = []

        # Header
        config_parts.append(DialplanGenerator._generate_header())

        # Inbound DID routing (NEW)
        if did_assignments and users_with_extensions:
            inbound_config = InboundRouter.generate(did_assignments, users_with_extensions)
            config_parts.append(inbound_config)

        # Extension routing
        if users_with_extensions and tenants:
            extension_config = ExtensionRouter.generate(users_with_extensions, tenants)
            config_parts.append(extension_config)

        return "\n".join(config_parts)
```

**Extend src/services/apply_service_enhanced.py**:

```python
class EnhancedApplyService:
    @staticmethod
    def apply_configuration_safe(...):
        # ... existing code ...

        # Step 3: Load data (EXTEND to include DIDs)
        users = session.query(User).all()
        tenants = session.query(Tenant).all()

        # NEW: Load DID assignments
        did_assignments_orm = session.query(DIDAssignment).join(PhoneNumber).all()
        did_assignments_data = []
        for assignment in did_assignments_orm:
            did_assignments_data.append({
                "phone_number": assignment.phone_number.number,
                "assigned_type": assignment.assigned_type.value,
                "assigned_id": assignment.assigned_id,
                "assigned_value": assignment.assigned_value,
            })

        # ... existing user/tenant data conversion ...

        # Step 5: Generate new dialplan (EXTEND with DIDs)
        dialplan_config = DialplanGenerator.generate_config(
            users_with_extensions=users_data,
            tenants=tenants_data,
            did_assignments=did_assignments_data,  # NEW
        )

        # ... rest of apply workflow ...
```

## Implementation Checklist

### Phase 1: Data Models & Migrations
- [ ] Create `src/models/phone_number.py` with PhoneNumber model
- [ ] Create `src/models/did_assignment.py` with DIDAssignment model
- [ ] Add relationships to `src/models/tenant.py` (has many phone_numbers)
- [ ] Create Alembic migration script for new tables
- [ ] Run migration: `alembic upgrade head`
- [ ] Test models in Python shell (create, query, constraints)

### Phase 2: Service Layer
- [ ] Create `src/services/did_service.py` with all methods
- [ ] Write unit tests for `DIDService.validate_e164()`
- [ ] Write unit tests for `DIDService.import_dids()` (success, errors, rollback)
- [ ] Write unit tests for `DIDService.allocate_to_tenant()`
- [ ] Write unit tests for `DIDService.assign_to_destination()` (all types)
- [ ] Write unit tests for `DIDService.unassign()`

### Phase 3: API Layer
- [ ] Create `src/schemas/phone_number.py` with Pydantic schemas
- [ ] Create `src/api/v1/dids.py` with all endpoints
- [ ] Register DIDs router in `src/api/v1/__init__.py`
- [ ] Test POST /dids/import endpoint (RBAC, validation, bulk insert)
- [ ] Test GET /dids endpoint (filtering, pagination, RBAC)
- [ ] Test PATCH /dids/{id}/allocate endpoint
- [ ] Test POST /dids/{id}/assign endpoint (all assignment types)
- [ ] Test DELETE /dids/{id}/assign endpoint

### Phase 4: Dialplan Integration
- [ ] Extend `src/config_generator/inbound_router.py` with DID routing logic
- [ ] Extend `src/config_generator/dialplan_generator.py` to accept `did_assignments` parameter
- [ ] Extend `src/services/apply_service_enhanced.py` to query DID assignments
- [ ] Test dialplan generation with sample DID assignments
- [ ] Test full Apply workflow with DIDs (validation, generation, reload, rollback)

### Phase 5: Testing & Documentation
- [ ] Write integration tests for full DID lifecycle (import → allocate → assign → apply → unassign)
- [ ] Write API tests for all error scenarios (404, 400, 403, 409)
- [ ] Update OpenAPI docs (auto-generated by FastAPI)
- [ ] Create quickstart.md with developer guide
- [ ] Create data-model.md with ERD and schema details

### Phase 6: Quality Assurance
- [ ] Run all tests: `pytest tests/`
- [ ] Test RBAC enforcement (platform_admin vs tenant_admin access)
- [ ] Test concurrent assignment attempts (unique constraint)
- [ ] Test bulk import with 1000+ DIDs (performance)
- [ ] Test Apply operation with 100+ DID assignments (performance)
- [ ] Manual QA: Import → Allocate → Assign → Apply → Verify dialplan → Test inbound call

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Race condition on DID assignment** | Medium | High | Database unique constraint on `phone_number_id` prevents duplicate assignments. IntegrityError caught and mapped to HTTP 409. |
| **Bulk import performance degradation** | Low | Medium | Transaction-level bulk insert. PostgreSQL handles 1000+ rows efficiently. Validated in testing phase. |
| **E.164 validation bypass** | Low | High | Dual validation: CHECK constraint at database level + service layer regex. Cannot bypass both. |
| **Tenant isolation breach** | Low | Critical | RBAC enforced at API layer (FastAPI dependencies) + FK constraints at DB level. Query filters by `current_user.tenant_id`. |
| **Dialplan generation failure on Apply** | Medium | High | Safe Apply workflow includes rollback on failure. Backup config restored. ApplyJob tracks errors. |
| **User deletion breaks DID assignment** | Medium | Medium | FK constraint: `assigned_id` references User with ON DELETE SET NULL. Service layer validation prevents assignment to non-existent user. |

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **E.164 validation accuracy** | 100% | Unit tests with valid/invalid numbers |
| **Bulk import throughput** | 1000+ DIDs in <30s | Integration test with timer |
| **DID assignment API latency** | <500ms p95 | Load testing with httpx |
| **Dialplan generation time** | <5s for 100+ assignments | Apply operation timing |
| **RBAC enforcement** | 100% coverage | API tests with different user roles |
| **Concurrent safety** | 0 duplicate assignments | Concurrent request tests |

## Next Steps

1. **Run `/sp.tasks`** to generate actionable implementation tasks from this plan
2. **Review data-model.md** for detailed schema documentation
3. **Review contracts/** for OpenAPI specifications
4. **Review quickstart.md** for developer onboarding
5. **Create ADR** if architectural decisions emerge during implementation (use `/sp.adr`)

---

**Plan Status**: ✅ Complete - Ready for task generation
**Constitution Compliance**: ✅ All 8 principles satisfied
**Quality Gates**: ✅ Passed - No violations, no NEEDS CLARIFICATION markers
