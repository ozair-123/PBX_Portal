# Research: DID Inventory & Inbound Routing Management

**Feature**: DID Inventory & Inbound Routing Management
**Date**: 2026-01-06
**Branch**: `002-did-inbound-routing`

## Purpose

This document consolidates research findings for technical decisions made during the planning phase. All research areas identified as "NEEDS CLARIFICATION" in the initial Technical Context have been resolved.

## Research Areas

### 1. E.164 Phone Number Format Validation

**Question**: What is the best approach to validate international phone numbers for consistency and storage?

**Decision**: Use regex `^\+[1-9]\d{1,14}$` with Python's `re` module

**Research Findings**:
- **E.164 Standard** (ITU-T): International phone number format
  - Structure: `+` + Country Code (1-3 digits) + Subscriber Number
  - Total length: Max 15 digits (including country code)
  - Leading `+` required, leading zero prohibited
  - Examples: `+1555123456 7` (US), `+442071234567` (UK), `+8613800138000` (China)

- **Storage Requirements**:
  - PostgreSQL `VARCHAR(16)` accommodates `+` + 15 digits
  - Indexed for fast lookup (unique constraint on `number` column)

- **Validation Strategy** (defense in depth):
  1. **Pydantic schema**: Validates at API boundary (immediate HTTP 400 feedback)
  2. **Service layer**: `DIDService.validate_e164()` regex check (business logic validation)
  3. **Database CHECK constraint**: PostgreSQL regex `number ~ '^\+[1-9]\d{1,14}$'` (last line of defense)

**Alternatives Considered**:

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Google phonenumbers library** | Comprehensive validation, formatting, country-specific rules | 8MB+ library, slow parsing, overkill for DID storage | ❌ **Rejected** - Adds heavy dependency for simple validation |
| **Database CHECK constraint only** | Simple, enforced at storage level | Poor error messages, can't provide field-level feedback to API | ❌ **Rejected** - User experience suffers |
| **Regex in service layer only** | Fast, no dependencies | Can be bypassed if direct DB access occurs | ❌ **Rejected** - No defense in depth |
| **Regex + CHECK constraint** (chosen) | Defense in depth, clear error messages, no dependencies | Requires maintaining regex in 2 places | ✅ **Selected** - Best balance of safety and simplicity |

**Implementation**:
```python
# Service layer
class DIDService:
    E164_REGEX = re.compile(r'^\+[1-9]\d{1,14}$')

    @staticmethod
    def validate_e164(number: str) -> bool:
        return bool(DIDService.E164_REGEX.match(number))

# Pydantic schema
class DIDImportItem(BaseModel):
    number: str

    @field_validator('number')
    @classmethod
    def validate_e164(cls, v: str) -> str:
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError(f"Invalid E.164 format: {v}")
        return v

# Database CHECK constraint
CheckConstraint("number ~ '^\\+[1-9]\\d{1,14}$'", name="phone_number_e164_format")
```

---

### 2. Bulk Import Strategy

**Question**: How should the system handle bulk import of 1000+ DIDs with potential validation errors?

**Decision**: Single transaction bulk insert with all-or-nothing rollback semantics

**Research Findings**:
- **PostgreSQL Performance**: Handles 1000+ row inserts in single transaction efficiently (<5s for 10K rows)
- **Transaction Semantics**: ACID guarantees prevent partial imports
- **Error Handling**: Validation errors collected, transaction rolled back, full error report returned to user

**Alternatives Considered**:

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Partial import with error report** | Flexible, some DIDs imported even with errors | Inconsistent state, requires manual cleanup, audit trail unclear | ❌ **Rejected** - Violates atomicity principle |
| **Batch commits (100 at a time)** | Limits transaction size, potential for progress tracking | Complex rollback logic, partial success hard to reason about | ❌ **Rejected** - Adds unnecessary complexity |
| **Single transaction, all-or-nothing** (chosen) | Simple, atomic, no cleanup required, clear success/failure | All DIDs must be valid | ✅ **Selected** - Aligns with Constitution Principle VIII (Simplicity First) |

**Implementation**:
```python
def import_dids(session, dids, actor_id):
    imported = 0
    errors = []

    try:
        for did_data in dids:
            # Validate E.164
            if not validate_e164(did_data["number"]):
                errors.append(f"Invalid E.164: {did_data['number']}")
                continue

            # Check duplicate
            if exists(did_data["number"]):
                errors.append(f"Duplicate: {did_data['number']}")
                continue

            session.add(PhoneNumber(...))
            imported += 1

        # Rollback if ANY errors
        if errors:
            session.rollback()
            return {"imported": 0, "failed": len(errors), "errors": errors}

        session.commit()
        return {"imported": imported, "failed": 0, "errors": []}

    except Exception as e:
        session.rollback()
        raise
```

**Performance Validation**: Target <30s for 1000 DIDs (includes validation + insert)

---

### 3. DID Assignment Locking Strategy

**Question**: How to prevent race conditions when multiple admins attempt to assign the same DID simultaneously?

**Decision**: Database unique constraint on `phone_number_id` column (one active assignment per DID)

**Research Findings**:
- **PostgreSQL Unique Constraints**: Atomic enforcement at database level (no application-level coordination needed)
- **Error Handling**: IntegrityError caught → mapped to HTTP 409 Conflict
- **Performance**: No lock contention (fails fast, no blocking)

**Alternatives Considered**:

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Row-level SELECT FOR UPDATE** | Explicit lock, prevents reads during assignment | Lock contention, requires explicit transaction management, overkill for uniqueness | ❌ **Rejected** - Adds complexity for simple constraint |
| **PostgreSQL advisory locks** | Serializes all assignments globally | Global bottleneck, reduces concurrency, unnecessary for per-DID operations | ❌ **Rejected** - Over-engineered |
| **Unique constraint** (chosen) | Atomic, fast, no lock contention, enforced by database | None (this is a best practice) | ✅ **Selected** - Simplest, most reliable |

**Implementation**:
```python
# Model
class DIDAssignment(Base):
    phone_number_id = Column(UUID, ForeignKey("phone_numbers.id"), unique=True, nullable=False)

# Service layer
try:
    assignment = DIDAssignment(phone_number_id=did_id, ...)
    session.add(assignment)
    session.flush()
except IntegrityError:
    session.rollback()
    raise ValueError(f"DID {number} is already assigned")  # Maps to HTTP 409
```

---

### 4. Tenant Isolation for DIDs

**Question**: How to enforce multi-tenant isolation for DID allocation and assignment?

**Decision**: PhoneNumber.tenant_id (nullable FK) + status enum + API RBAC enforcement

**Research Findings**:
- **Lifecycle States**:
  - `UNASSIGNED`: `tenant_id = NULL` (global pool, platform admin only)
  - `ALLOCATED`: `tenant_id = <UUID>` (tenant pool, tenant admin can assign)
  - `ASSIGNED`: `tenant_id = <UUID>` + active DIDAssignment record
- **RBAC Enforcement**: FastAPI dependencies (`require_role()`) + query filters
- **Database Constraints**: CHECK constraint enforces `tenant_id` consistency with status

**Alternatives Considered**:

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Separate tables** (global_dids, tenant_dids) | Physical separation | Schema duplication, complex queries, migration overhead when allocating | ❌ **Rejected** - Violates DRY |
| **View-based isolation** | Single table, filtered views per tenant | Implicit filtering error-prone, harder to audit | ❌ **Rejected** - Obscures data access patterns |
| **Nullable tenant_id + status enum** (chosen) | Explicit lifecycle, single source of truth, clear queries | Requires CHECK constraint for consistency | ✅ **Selected** - Explicit, auditable, simple |

**Implementation**:
```python
# Model
class PhoneNumber(Base):
    status = Column(Enum(PhoneNumberStatus), nullable=False, default=UNASSIGNED)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(status = 'UNASSIGNED' AND tenant_id IS NULL) OR "
            "(status IN ('ALLOCATED', 'ASSIGNED') AND tenant_id IS NOT NULL)",
            name="phone_number_tenant_consistency"
        ),
    )

# API layer
@router.get("/dids")
async def list_dids(
    tenant_id: Optional[UUID] = None,
    current_user: dict = Depends(require_role("support")),
    db: Session = Depends(get_db),
):
    query = db.query(PhoneNumber)

    # Auto-filter for tenant admins
    if current_user["role"] == "tenant_admin":
        tenant_id = UUID(current_user["tenant_id"])

    if tenant_id:
        query = query.filter(PhoneNumber.tenant_id == tenant_id)

    return query.all()
```

---

### 5. Dialplan Generation Integration

**Question**: How to extend the existing dialplan generator to include DID-to-destination routing?

**Decision**: Extend `InboundRouter.generate()` to query DIDAssignment table and generate [from-trunk-external] context

**Research Findings**:
- **Existing Architecture**: `DialplanGenerator` orchestrates multiple sub-generators (InboundRouter, ExtensionRouter, OutboundPolicyGenerator)
- **[from-trunk-external] Context**: Asterisk entry point for incoming SIP trunk calls
- **Routing Format**: `exten => +15551234567,1,Goto(tenant-acme,1001,1)` (DID → tenant context → extension)

**Alternatives Considered**:

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **New DIDRouter class** | Clean separation of concerns | Duplicates context management logic, violates DRY | ❌ **Rejected** - Adds unnecessary abstraction |
| **Inline in DialplanGenerator** | No new class | Violates single responsibility, hard to test | ❌ **Rejected** - Anti-pattern |
| **Extend InboundRouter** (chosen) | Reuses existing router, logical grouping (inbound = external calls) | InboundRouter name ambiguous (could rename to ExternalRouter) | ✅ **Selected** - Simplest, leverages existing code |

**Implementation**:
```python
class InboundRouter:
    @staticmethod
    def generate(did_assignments: List[Dict], users: List[Dict]) -> str:
        config = []
        config.append("[from-trunk-external]")

        for assignment in did_assignments:
            number = assignment["phone_number"]

            if assignment["assigned_type"] == "USER":
                user = find_user(users, assignment["assigned_id"])
                tenant_context = f"tenant-{user['tenant_id']}"
                config.append(f"exten => {number},1,Goto({tenant_context},{user['extension']},1)")

            elif assignment["assigned_type"] == "EXTERNAL":
                config.append(f"exten => {number},1,{assignment['assigned_value']}")

        return "\n".join(config)

# Extend Apply Service
class EnhancedApplyService:
    def apply_configuration_safe(...):
        did_assignments = session.query(DIDAssignment).join(PhoneNumber).all()
        dialplan = DialplanGenerator.generate_config(
            users=users_data,
            tenants=tenants_data,
            did_assignments=did_assignments_data,  # NEW
        )
```

---

### 6. Assignment Type Handling

**Question**: How to handle polymorphic DID assignments (USER, IVR, QUEUE, EXTERNAL) in a single table?

**Decision**: `assigned_type` (enum) + `assigned_id` (UUID) / `assigned_value` (string) with CHECK constraint

**Research Findings**:
- **Polymorphic Pattern**: Single table with type discriminator + conditional fields
- **Type Safety**: CHECK constraint enforces `assigned_id` XOR `assigned_value` based on `assigned_type`
- **Referential Integrity**: `assigned_id` can FK to User/IVR/Queue (future), `assigned_value` for arbitrary dialplan

**Alternatives Considered**:

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Separate tables per type** (user_assignments, ivr_assignments, etc.) | Type safety, clear schema | Schema explosion, complex queries (UNIONs), violates DRY | ❌ **Rejected** - Over-engineered |
| **JSONB config field** | Flexible, extensible | Loses type safety, no referential integrity, hard to query | ❌ **Rejected** - Anti-pattern for structured data |
| **Type + conditional fields** (chosen) | Balance of flexibility and type safety, single query | Requires CHECK constraint | ✅ **Selected** - Standard polymorphic pattern |

**Implementation**:
```python
class AssignmentType(enum.Enum):
    USER = "USER"
    IVR = "IVR"
    QUEUE = "QUEUE"
    EXTERNAL = "EXTERNAL"

class DIDAssignment(Base):
    assigned_type = Column(Enum(AssignmentType), nullable=False)
    assigned_id = Column(UUID, nullable=True)  # For USER/IVR/QUEUE
    assigned_value = Column(String(255), nullable=True)  # For EXTERNAL

    __table_args__ = (
        CheckConstraint(
            "(assigned_type IN ('USER', 'IVR', 'QUEUE') AND assigned_id IS NOT NULL AND assigned_value IS NULL) OR "
            "(assigned_type = 'EXTERNAL' AND assigned_id IS NULL AND assigned_value IS NOT NULL)",
            name="did_assignment_type_consistency"
        ),
    )
```

**Validation Logic**:
```python
def assign_to_destination(session, phone_number_id, assigned_type, assigned_id=None, assigned_value=None):
    if assigned_type == AssignmentType.USER:
        if not assigned_id:
            raise ValueError("assigned_id required for USER")
        user = session.query(User).get(assigned_id)
        if not user:
            raise ValueError("User not found")
        if user.tenant_id != phone_number.tenant_id:
            raise ValueError("User not in same tenant")

    elif assigned_type == AssignmentType.EXTERNAL:
        if not assigned_value:
            raise ValueError("assigned_value required for EXTERNAL")

    assignment = DIDAssignment(
        phone_number_id=phone_number_id,
        assigned_type=assigned_type,
        assigned_id=assigned_id,
        assigned_value=assigned_value,
    )
    session.add(assignment)
```

---

## Technology Stack Confirmation

**No new external dependencies required.** All research confirms existing stack is sufficient:

| Technology | Version | Usage | Status |
|------------|---------|-------|--------|
| Python | 3.11+ | Language | ✅ Existing |
| FastAPI | 0.104+ | Web framework, OpenAPI generation | ✅ Existing |
| SQLAlchemy | 2.0+ | ORM, migrations | ✅ Existing |
| PostgreSQL | 14+ | Database (JSONB, UUID, CHECK constraints, advisory locks) | ✅ Existing |
| Pydantic | 2.0+ | Schema validation | ✅ Existing |
| Alembic | 1.12+ | Database migrations | ✅ Existing |
| pytest | 7.0+ | Testing framework | ✅ Existing |
| httpx | - | Async HTTP client for API tests | ✅ Existing |

**Python Standard Library** (`re` module) used for E.164 regex validation.

---

## Best Practices Applied

### 1. Defense in Depth (Validation)
- **Layer 1**: Pydantic schema at API boundary
- **Layer 2**: Service layer business logic validation
- **Layer 3**: Database CHECK constraints

### 2. Fail Fast (Error Handling)
- E.164 validation errors: Immediate HTTP 400 with specific error message
- Duplicate DID assignment: Database unique constraint → IntegrityError → HTTP 409
- RBAC violations: FastAPI dependency → HTTP 403

### 3. Atomicity (Transactions)
- Bulk import: Single transaction, all-or-nothing semantics
- Assignment operations: Session.flush() after mutation, commit only on success

### 4. Simplicity First (Constitution Principle VIII)
- Regex validation instead of heavy library
- Database constraints instead of application locking
- Single table for assignments instead of per-type tables

### 5. Explicit Over Implicit (Constitution Principle IV)
- Status transitions (UNASSIGNED → ALLOCATED → ASSIGNED) are explicit
- DID assignments take effect only via explicit Apply action
- No automatic Asterisk reloads

---

## Performance Targets Validation

| Target | Research Finding | Status |
|--------|------------------|--------|
| Import 1000+ DIDs in <30s | PostgreSQL bulk insert benchmark: ~10K rows in 5s | ✅ Achievable |
| DID assignment API <500ms p95 | Single INSERT + UPDATE, indexed FK lookups | ✅ Achievable |
| List/filter 5000+ DIDs <2s | Indexed queries (status, tenant_id, number), pagination | ✅ Achievable |
| Dialplan generation <5s for 100+ assignments | String concatenation, no external calls | ✅ Achievable |

---

## Risks Mitigated

| Risk | Mitigation Strategy |
|------|---------------------|
| **Race condition on DID assignment** | Database unique constraint (atomic enforcement) |
| **E.164 validation bypass** | Triple validation (Pydantic + Service + DB CHECK) |
| **Tenant isolation breach** | RBAC at API layer + FK constraints + query filters |
| **Partial bulk import** | Single transaction with rollback on any error |
| **User deletion breaks assignment** | FK with ON DELETE SET NULL + validation at assignment time |

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Should IVR and QUEUE entities be implemented now? | ❌ **No** - Out of scope for this feature. Use EXTERNAL assignment type with dialplan string until those entities exist (future work). |
| Should we support number portability tracking? | ❌ **No** - Use `provider_metadata` JSONB field for carrier-specific data if needed. Not a requirement in spec. |
| Should we support DID reservations (pending activation)? | ❌ **No** - UNASSIGNED status is sufficient. No reservation workflow specified. |

---

## References

- **E.164 Standard**: ITU-T Recommendation E.164 (International Public Telecommunication Numbering Plan)
- **PostgreSQL Documentation**: Constraints, JSONB, Advisory Locks
- **FastAPI Documentation**: Dependencies, RBAC, OpenAPI schema generation
- **SQLAlchemy Documentation**: Polymorphic patterns, CHECK constraints, relationship management

---

**Research Status**: ✅ Complete
**All NEEDS CLARIFICATION items resolved**: ✅ Yes
**Ready for implementation**: ✅ Yes
