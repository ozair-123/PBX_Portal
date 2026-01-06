# Data Model: DID Inventory & Inbound Routing Management

**Feature**: DID Inventory & Inbound Routing Management
**Date**: 2026-01-06
**Branch**: `002-did-inbound-routing`

## Overview

This feature introduces two new entities to manage the DID (Direct Inward Dialing) lifecycle:

1. **PhoneNumber**: Inventory of DIDs with lifecycle tracking (UNASSIGNED → ALLOCATED → ASSIGNED)
2. **DIDAssignment**: Mapping of DIDs to destinations (users, IVRs, queues, external dialplan)

## Entity Relationship Diagram

```
┌─────────────────┐              ┌──────────────────┐              ┌──────────────────┐
│     Tenant      │              │   PhoneNumber    │              │  DIDAssignment   │
│─────────────────│              │──────────────────│              │──────────────────│
│ id (PK)         │1            *│ id (PK)          │1            ?│ id (PK)          │
│ name            │──────────────│ number (unique)  │──────────────│ phone_number_id  │
│ ext_min         │              │ status (enum)    │              │ assigned_type    │
│ ext_max         │              │ tenant_id (FK)   │              │ assigned_id      │
│ ...             │              │ provider         │              │ assigned_value   │
└─────────────────┘              │ provider_metadata│              │ created_by (FK)  │
                                 │ created_at       │              │ created_at       │
                                 │ updated_at       │              │ updated_at       │
                                 └──────────────────┘              └──────────────────│
                                         │                                  │
                                         │                                  │
                                         │assigned_id (conditional FK)      │
                                         │                                  │
┌─────────────────┐                     └──────────────────────────────────┘
│      User       │
│─────────────────│
│ id (PK)         │*
│ tenant_id (FK)  │
│ email (unique)  │
│ extension       │
│ ...             │
└─────────────────┘
```

**Key Relationships**:
- Tenant **has many** PhoneNumbers (1:*)
- PhoneNumber **has one** DIDAssignment (1:?)  (optional, only when status=ASSIGNED)
- DIDAssignment **belongs to** PhoneNumber (via phone_number_id unique FK)
- DIDAssignment **conditionally references** User (via assigned_id, only when assigned_type=USER)
- User **created** DIDAssignment (audit trail via created_by FK)

## Entity Definitions

### PhoneNumber

**Purpose**: Represents a phone number (DID) in the system inventory with lifecycle state tracking.

**Table Name**: `phone_numbers`

**Lifecycle States**:
1. **UNASSIGNED**: Number in global pool (`tenant_id = NULL`), available for platform admin allocation
2. **ALLOCATED**: Number assigned to tenant (`tenant_id = <UUID>`), available for tenant admin to assign to destinations
3. **ASSIGNED**: Number assigned to user/IVR/queue/external (`tenant_id = <UUID>`, DIDAssignment exists)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `number` | VARCHAR(16) | UNIQUE, NOT NULL, CHECK (E.164 format) | Phone number in E.164 format (e.g., +15551234567) |
| `status` | ENUM(PhoneNumberStatus) | NOT NULL, DEFAULT 'UNASSIGNED' | Lifecycle state |
| `tenant_id` | UUID | FOREIGN KEY(tenants.id) ON DELETE SET NULL, NULLABLE | Owning tenant (NULL when UNASSIGNED) |
| `provider` | VARCHAR(255) | NULLABLE | Carrier name (e.g., "Twilio", "Bandwidth") |
| `provider_metadata` | JSONB | NULLABLE, DEFAULT '{}' | Flexible carrier-specific metadata |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW(), ON UPDATE NOW() | Last modification timestamp |

**Indexes**:
- `idx_phone_numbers_number` (UNIQUE) on `number`
- `idx_phone_numbers_status` on `status`
- `idx_phone_numbers_tenant_id` on `tenant_id`
- `idx_phone_numbers_tenant_status` (COMPOSITE) on `(tenant_id, status)` - For tenant admin queries

**Constraints**:
- **phone_number_e164_format**: `CHECK (number ~ '^\+[1-9]\d{1,14}$')`
  - Enforces E.164 international format
  - Leading `+` required, leading zero prohibited
  - Max 15 digits

- **phone_number_tenant_consistency**: `CHECK ((status = 'UNASSIGNED' AND tenant_id IS NULL) OR (status IN ('ALLOCATED', 'ASSIGNED') AND tenant_id IS NOT NULL))`
  - Enforces tenant_id consistency with lifecycle state
  - UNASSIGNED numbers must have NULL tenant_id
  - ALLOCATED/ASSIGNED numbers must have non-NULL tenant_id

**Enum: PhoneNumberStatus**
```python
class PhoneNumberStatus(enum.Enum):
    UNASSIGNED = "UNASSIGNED"  # Global pool, platform admin only
    ALLOCATED = "ALLOCATED"    # Tenant pool, tenant admin can assign
    ASSIGNED = "ASSIGNED"      # Assigned to destination, in use
```

**Example Rows**:
```
| id (UUID) | number         | status      | tenant_id | provider | provider_metadata            | created_at          | updated_at          |
|-----------|----------------|-------------|-----------|----------|------------------------------|---------------------|---------------------|
| uuid-1    | +15551234567   | UNASSIGNED  | NULL      | Twilio   | {"account_sid": "AC123"}     | 2026-01-06 10:00:00 | 2026-01-06 10:00:00 |
| uuid-2    | +15559876543   | ALLOCATED   | uuid-t1   | Bandwidth| {"order_id": "ORD789"}       | 2026-01-06 10:05:00 | 2026-01-06 10:10:00 |
| uuid-3    | +14441112222   | ASSIGNED    | uuid-t1   | Twilio   | {"sid": "PN456"}             | 2026-01-06 10:15:00 | 2026-01-06 10:20:00 |
```

---

### DIDAssignment

**Purpose**: Maps a phone number to its routing destination (user extension, IVR, queue, or external dialplan).

**Table Name**: `did_assignments`

**Assignment Types**:
1. **USER**: Route to user extension → `assigned_id` references User.id
2. **IVR**: Route to auto-attendant → `assigned_id` references IVR.id (future entity)
3. **QUEUE**: Route to call queue → `assigned_id` references Queue.id (future entity)
4. **EXTERNAL**: Route to arbitrary dialplan → `assigned_value` contains dialplan string (e.g., "VoiceMail(2000@tenant-acme)")

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `phone_number_id` | UUID | FOREIGN KEY(phone_numbers.id) ON DELETE CASCADE, UNIQUE, NOT NULL | Phone number being assigned (one assignment per DID) |
| `assigned_type` | ENUM(AssignmentType) | NOT NULL | Type of destination |
| `assigned_id` | UUID | NULLABLE | Destination entity ID (for USER/IVR/QUEUE) |
| `assigned_value` | VARCHAR(255) | NULLABLE | Dialplan string (for EXTERNAL) |
| `created_by` | UUID | FOREIGN KEY(users.id) ON DELETE SET NULL, NULLABLE | User who created the assignment (audit trail) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW(), ON UPDATE NOW() | Last modification timestamp |

**Indexes**:
- `idx_did_assignments_phone_number_id` (UNIQUE) on `phone_number_id`

**Constraints**:
- **UNIQUE**: `phone_number_id` - One active assignment per phone number
- **did_assignment_type_consistency**: `CHECK ((assigned_type IN ('USER', 'IVR', 'QUEUE') AND assigned_id IS NOT NULL AND assigned_value IS NULL) OR (assigned_type = 'EXTERNAL' AND assigned_id IS NULL AND assigned_value IS NOT NULL))`
  - Enforces polymorphic field usage
  - USER/IVR/QUEUE: `assigned_id` required, `assigned_value` must be NULL
  - EXTERNAL: `assigned_value` required, `assigned_id` must be NULL

**Enum: AssignmentType**
```python
class AssignmentType(enum.Enum):
    USER = "USER"          # Route to user extension
    IVR = "IVR"            # Route to auto-attendant
    QUEUE = "QUEUE"        # Route to call queue
    EXTERNAL = "EXTERNAL"  # Route to arbitrary dialplan destination
```

**Example Rows**:
```
| id (UUID) | phone_number_id | assigned_type | assigned_id | assigned_value                 | created_by | created_at          | updated_at          |
|-----------|-----------------|---------------|-------------|--------------------------------|------------|---------------------|---------------------|
| uuid-a1   | uuid-3          | USER          | uuid-u1     | NULL                           | uuid-admin | 2026-01-06 10:20:00 | 2026-01-06 10:20:00 |
| uuid-a2   | uuid-4          | EXTERNAL      | NULL        | VoiceMail(2000@tenant-acme)    | uuid-admin | 2026-01-06 10:25:00 | 2026-01-06 10:25:00 |
```

**Generated Dialplan** (from above assignments):
```
[from-trunk-external]
; DID uuid-3 (+14441112222) → USER uuid-u1 (extension 1001 in tenant-acme)
exten => +14441112222,1,Goto(tenant-acme,1001,1)

; DID uuid-4 (+15558889999) → EXTERNAL (voicemail box 2000)
exten => +15558889999,1,VoiceMail(2000@tenant-acme)
```

---

## State Transitions

### PhoneNumber Lifecycle

```
        ┌─────────────┐
        │ UNASSIGNED  │ (tenant_id = NULL)
        └──────┬──────┘
               │ Platform Admin allocates to Tenant
               │ API: PATCH /dids/{id}/allocate
               ▼
        ┌─────────────┐
        │  ALLOCATED  │ (tenant_id = <UUID>)
        └──────┬──────┘
               │ Tenant Admin assigns to User/IVR/Queue/External
               │ API: POST /dids/{id}/assign
               ▼
        ┌─────────────┐
        │  ASSIGNED   │ (tenant_id = <UUID>, DIDAssignment exists)
        └──────┬──────┘
               │ Tenant Admin unassigns
               │ API: DELETE /dids/{id}/assign
               ▼
        ┌─────────────┐
        │  ALLOCATED  │ (DIDAssignment deleted, tenant_id preserved)
        └──────┬──────┘
               │ Platform Admin deallocates
               │ API: PATCH /dids/{id}/deallocate
               ▼
        ┌─────────────┐
        │ UNASSIGNED  │ (tenant_id = NULL)
        └─────────────┘
```

**Transition Rules**:
1. **Import** → UNASSIGNED (tenant_id = NULL)
2. **Allocate** → UNASSIGNED → ALLOCATED (sets tenant_id)
3. **Assign** → ALLOCATED → ASSIGNED (creates DIDAssignment, validates destination exists)
4. **Unassign** → ASSIGNED → ALLOCATED (deletes DIDAssignment, preserves tenant_id)
5. **Deallocate** → ALLOCATED → UNASSIGNED (clears tenant_id, requires no active assignment)

---

## Data Integrity Rules

### 1. E.164 Format Validation
- **Where**: Pydantic schema, service layer, database CHECK constraint
- **Pattern**: `^\+[1-9]\d{1,14}$`
- **Examples**:
  - ✅ Valid: `+15551234567`, `+442071234567`, `+8613800138000`
  - ❌ Invalid: `15551234567` (no `+`), `+01234567890` (leading zero), `+123456789012345678` (too long)

### 2. Unique Phone Numbers
- **Constraint**: UNIQUE index on `phone_numbers.number`
- **Purpose**: Prevents duplicate DIDs across all tenants
- **Error**: IntegrityError → HTTP 409 Conflict

### 3. Tenant Isolation
- **Constraint**: CHECK constraint `phone_number_tenant_consistency`
- **Purpose**: Enforces `tenant_id` consistency with `status`
- **Rules**:
  - UNASSIGNED: `tenant_id` MUST be NULL
  - ALLOCATED/ASSIGNED: `tenant_id` MUST be non-NULL

### 4. One Assignment Per DID
- **Constraint**: UNIQUE index on `did_assignments.phone_number_id`
- **Purpose**: Prevents race conditions where two admins assign same DID
- **Error**: IntegrityError → HTTP 409 Conflict

### 5. Assignment Type Consistency
- **Constraint**: CHECK constraint `did_assignment_type_consistency`
- **Purpose**: Enforces polymorphic field usage (`assigned_id` XOR `assigned_value`)
- **Rules**:
  - USER/IVR/QUEUE: `assigned_id` required, `assigned_value` NULL
  - EXTERNAL: `assigned_value` required, `assigned_id` NULL

### 6. Cascade Deletes
- **PhoneNumber → DIDAssignment**: ON DELETE CASCADE (deleting PhoneNumber deletes assignment)
- **Tenant → PhoneNumber**: ON DELETE SET NULL (deleting Tenant deallocates DIDs back to global pool)
- **User → DIDAssignment.created_by**: ON DELETE SET NULL (deleting User preserves audit trail but nulls creator reference)

### 7. Assignment Destination Validation
- **Business Logic**: Service layer validates destination exists and belongs to same tenant
- **Example**: When `assigned_type = USER`, validate:
  1. User with `assigned_id` exists
  2. User.tenant_id == PhoneNumber.tenant_id
  3. User.status == 'active'

---

## Query Patterns

### 1. List UNASSIGNED DIDs (Platform Admin)
```sql
SELECT * FROM phone_numbers
WHERE status = 'UNASSIGNED'
ORDER BY created_at DESC
LIMIT 50;
```

### 2. List ALLOCATED DIDs for Tenant (Tenant Admin)
```sql
SELECT * FROM phone_numbers
WHERE tenant_id = ? AND status IN ('ALLOCATED', 'ASSIGNED')
ORDER BY number
LIMIT 50 OFFSET ?;
```

### 3. Get DID with Assignment
```sql
SELECT pn.*, da.*
FROM phone_numbers pn
LEFT JOIN did_assignments da ON da.phone_number_id = pn.id
WHERE pn.id = ?;
```

### 4. Search DIDs by Partial Number
```sql
SELECT * FROM phone_numbers
WHERE number LIKE '%555%'  -- Finds all numbers containing "555"
ORDER BY number
LIMIT 50;
```

### 5. Get All DID Assignments for Apply
```sql
SELECT
  pn.number as phone_number,
  da.assigned_type,
  da.assigned_id,
  da.assigned_value
FROM did_assignments da
JOIN phone_numbers pn ON pn.id = da.phone_number_id
WHERE da.assigned_type IN ('USER', 'EXTERNAL')  -- Only types we support in dialplan now
ORDER BY pn.number;
```

---

## Migration Strategy

**Alembic Migration**: Create tables with all constraints

```python
"""Add DID management models

Revision ID: 20260106_1200_add_did_models
Revises: <previous_revision>
Create Date: 2026-01-06 12:00:00
"""

def upgrade():
    # Create phone_numbers table
    op.create_table(
        'phone_numbers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('number', sa.String(16), unique=True, nullable=False),
        sa.Column('status', sa.Enum('UNASSIGNED', 'ALLOCATED', 'ASSIGNED', name='phonenumberstatus'), nullable=False, server_default='UNASSIGNED'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(255), nullable=True),
        sa.Column('provider_metadata', postgresql.JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint("number ~ '^\\+[1-9]\\d{1,14}$'", name='phone_number_e164_format'),
        sa.CheckConstraint(
            "(status = 'UNASSIGNED' AND tenant_id IS NULL) OR (status IN ('ALLOCATED', 'ASSIGNED') AND tenant_id IS NOT NULL)",
            name='phone_number_tenant_consistency'
        ),
    )

    # Create indexes
    op.create_index('idx_phone_numbers_number', 'phone_numbers', ['number'], unique=True)
    op.create_index('idx_phone_numbers_status', 'phone_numbers', ['status'])
    op.create_index('idx_phone_numbers_tenant_id', 'phone_numbers', ['tenant_id'])
    op.create_index('idx_phone_numbers_tenant_status', 'phone_numbers', ['tenant_id', 'status'])

    # Create did_assignments table
    op.create_table(
        'did_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
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

    # Create indexes
    op.create_index('idx_did_assignments_phone_number_id', 'did_assignments', ['phone_number_id'], unique=True)

def downgrade():
    op.drop_table('did_assignments')
    op.drop_table('phone_numbers')
    op.execute('DROP TYPE assignmenttype')
    op.execute('DROP TYPE phonenumberstatus')
```

---

**Data Model Status**: ✅ Complete
**Tables**: 2 (phone_numbers, did_assignments)
**Indexes**: 6 (performance optimized for tenant admin queries)
**Constraints**: 4 (E.164 format, tenant consistency, assignment uniqueness, type consistency)
