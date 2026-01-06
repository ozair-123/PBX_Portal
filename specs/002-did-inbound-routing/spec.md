# Feature Specification: DID Inventory & Inbound Routing Management

**Feature Branch**: `002-did-inbound-routing`
**Created**: 2026-01-06
**Status**: Draft
**Input**: User description: "Implement a comprehensive Number Management system to handle the lifecycle of DIDs (Direct Inward Dialing) for a multi-tenant PBX. This module bridges external SIP trunks to internal users, IVRs, and Queues."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Platform Admin Imports DID Inventory (Priority: P1)

As a platform administrator, I need to bulk import phone numbers from our carrier into the system so that they become available for tenant allocation and eventual assignment to users.

**Why this priority**: This is the foundation of the entire DID management workflow. Without imported numbers, no other stories can function. This is the entry point for all phone numbers into the system.

**Independent Test**: Can be fully tested by importing a CSV/JSON file with 100+ phone numbers and verifying they appear in the inventory with "UNASSIGNED" status. Delivers immediate value by creating the phone number pool.

**Acceptance Scenarios**:

1. **Given** a JSON file containing 500 DIDs in E.164 format, **When** platform admin uploads via `/api/v1/dids/import`, **Then** all valid numbers are stored with provider metadata and status=UNASSIGNED
2. **Given** an import file with duplicate numbers, **When** platform admin uploads, **Then** system returns validation errors identifying the duplicates without creating any records
3. **Given** an import file with invalid E.164 formats, **When** platform admin uploads, **Then** system rejects invalid entries and reports specific format violations
4. **Given** existing DIDs in the database, **When** platform admin re-imports the same file, **Then** system prevents duplicates and reports which numbers already exist

---

### User Story 2 - Platform Admin Allocates DIDs to Tenant (Priority: P2)

As a platform administrator, I need to allocate phone numbers from the global pool to specific tenants so that tenant admins can assign them to their users without accessing the entire inventory.

**Why this priority**: This enables multi-tenant isolation and delegation. Once implemented, tenant admins can self-serve DID assignments within their allocated pool, reducing platform admin workload.

**Independent Test**: Can be fully tested by allocating 10 DIDs to a tenant and verifying that tenant admins can only see/assign those numbers while other tenants cannot access them.

**Acceptance Scenarios**:

1. **Given** 20 UNASSIGNED DIDs in inventory, **When** platform admin allocates 10 to tenant "Acme Corp", **Then** those DIDs show tenant_id=acme and status=ALLOCATED, tenant admin sees them in their pool
2. **Given** a DID already allocated to tenant A, **When** platform admin attempts to allocate it to tenant B, **Then** system rejects with conflict error
3. **Given** a DID allocated to a tenant, **When** platform admin deallocates it, **Then** DID returns to global pool with status=UNASSIGNED and tenant_id=NULL

---

### User Story 3 - Tenant Admin Assigns DID to User (Priority: P1)

As a tenant administrator, I need to assign one of my allocated phone numbers to a specific user so that incoming calls to that number route directly to the user's extension.

**Why this priority**: This is the core business value - connecting external callers to internal users. This is what enables the PBX to function as a phone system.

**Independent Test**: Can be fully tested by assigning a DID to a user, triggering apply, and verifying that calls to that number route to the user's extension in the generated dialplan.

**Acceptance Scenarios**:

1. **Given** user Alice with extension 1001, **When** tenant admin assigns DID +15551234567, **Then** assignment is created with assigned_type=USER, assigned_id=alice_uuid
2. **Given** DID +15551234567 assigned to Alice, **When** tenant admin calls "Apply Configuration", **Then** dialplan generates: exten => +15551234567,1,Goto(tenant-acme,1001,1)
3. **Given** DID +15551234567 assigned to Alice, **When** tenant admin unassigns it, **Then** assignment is deleted and next Apply removes routing from dialplan
4. **Given** DID +15551234567 assigned to Alice, **When** tenant admin attempts to assign it to Bob, **Then** system rejects with "DID already assigned" error

---

### User Story 4 - Tenant Admin Assigns DID to Voicemail (Priority: P3)

As a tenant administrator, I need to assign a phone number directly to a voicemail box so that callers can leave messages without ringing a user's phone.

**Why this priority**: This is a common use case for after-hours lines or dedicated message services, but less critical than user assignment. Can be added after core functionality is proven.

**Independent Test**: Can be fully tested by assigning a DID to voicemail box 2000 and verifying the generated dialplan routes to VoiceMail(2000@tenant-acme).

**Acceptance Scenarios**:

1. **Given** voicemail box 2000 exists, **When** tenant admin assigns DID +15559876543 to voicemail, **Then** assignment is created with assigned_type=EXTERNAL, assigned_value="VoiceMail(2000@tenant-acme)"
2. **Given** DID assigned to voicemail, **When** Apply runs, **Then** dialplan generates: exten => +15559876543,1,VoiceMail(2000@tenant-acme)

---

### User Story 5 - Safe Apply Triggers Inbound Routing Generation (Priority: P1)

As a tenant administrator, when I trigger "Apply Configuration", the system must generate Asterisk dialplan entries for all DID-to-destination mappings so that incoming calls route correctly.

**Why this priority**: This integrates DID management with the existing Safe Apply workflow. Without this, DID assignments have no effect on call routing.

**Independent Test**: Can be fully tested by creating 3 DID assignments (user, IVR, external), running Apply, and verifying the generated extensions_custom.conf contains correct [from-trunk-external] entries.

**Acceptance Scenarios**:

1. **Given** 3 DIDs assigned (1 to user, 1 to IVR, 1 to external), **When** Apply runs, **Then** dialplan contains [from-trunk-external] context with 3 exten entries
2. **Given** no DIDs assigned, **When** Apply runs, **Then** [from-trunk-external] context exists but is empty
3. **Given** Apply fails validation, **When** rollback occurs, **Then** previous dialplan is restored with old DID routing intact

---

### User Story 6 - View DID Inventory with Filters (Priority: P2)

As a platform or tenant administrator, I need to view and filter the phone number inventory so that I can find available numbers or verify assignments.

**Why this priority**: This is a usability enhancement that makes the system practical for production use with large inventories. Critical for day-to-day operations but not blocking for MVP.

**Independent Test**: Can be fully tested by querying `/api/v1/dids?status=UNASSIGNED&tenant_id=acme` and verifying results match filter criteria.

**Acceptance Scenarios**:

1. **Given** 100 DIDs (50 UNASSIGNED, 30 ALLOCATED, 20 ASSIGNED), **When** platform admin filters by status=UNASSIGNED, **Then** API returns exactly 50 results
2. **Given** tenant admin for Acme Corp, **When** querying DIDs without filters, **Then** only sees DIDs allocated to their tenant (no global pool access)
3. **Given** 200 DIDs, **When** platform admin paginates with page_size=20, **Then** receives results in pages with correct total count

---

### Edge Cases

- What happens when a DID is assigned to a user, then the user is deleted? (Assignment should block deletion or cascade to unassign)
- How does the system handle DIDs assigned to non-existent extensions? (Validation at assignment time must prevent this)
- What if two admins attempt to assign the same DID simultaneously? (Row-level locking or unique constraint must prevent race condition)
- What happens if bulk import contains 10,000 numbers and some fail validation? (Transaction rollback or partial import with error report?)
- How does dialplan generation handle international number formats with varying lengths? (E.164 validation ensures consistency)
- What if a tenant is deleted while DIDs are allocated to it? (Must deallocate DIDs back to global pool or block deletion)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate all phone numbers against E.164 format (regex: `^\+[1-9]\d{1,14}$`) before storage
- **FR-002**: System MUST support bulk import of DIDs via JSON payload with format: `[{"number": "+15551234567", "provider": "Twilio", "metadata": {...}}]`
- **FR-003**: System MUST prevent duplicate phone numbers across all tenants (unique constraint on number column)
- **FR-004**: Platform admins MUST be able to allocate UNASSIGNED DIDs to specific tenants
- **FR-005**: Tenant admins MUST only view and assign DIDs allocated to their own tenant (RBAC enforcement)
- **FR-006**: System MUST support assignment types: USER (internal extension), IVR (auto-attendant), QUEUE (call queue), EXTERNAL (arbitrary dialplan destination)
- **FR-007**: System MUST validate USER assignments against existing user extensions at assignment time
- **FR-008**: System MUST prevent assigning the same DID to multiple destinations (unique constraint on active assignments)
- **FR-009**: System MUST allow unassigning DIDs, returning them to ALLOCATED status for reassignment
- **FR-010**: System MUST generate [from-trunk-external] dialplan context entries for all active DID assignments during Apply
- **FR-011**: Generated dialplan entries MUST use format: `exten => <E164_NUMBER>,1,Goto(<tenant_context>,<extension>,1)` for USER assignments
- **FR-012**: System MUST integrate DID routing generation with existing Safe Apply workflow (validation, backup, rollback)
- **FR-013**: System MUST audit log all DID operations (import, allocate, assign, unassign) with actor and timestamp
- **FR-014**: System MUST support filtering DIDs by status (UNASSIGNED, ALLOCATED, ASSIGNED)
- **FR-015**: System MUST support filtering DIDs by tenant_id for platform admins
- **FR-016**: System MUST support pagination for DID list endpoints (default page_size=50, max=200)
- **FR-017**: System MUST return provider metadata in JSON format when querying DID details
- **FR-018**: System MUST prevent deallocating DIDs that have active assignments (business rule validation)
- **FR-019**: System MUST support searching DIDs by partial number match (e.g., "555" finds all numbers containing "555")
- **FR-020**: System MUST expose DID assignment status in user detail endpoints (GET /api/v1/users/{id})

### Key Entities *(include if feature involves data)*

- **PhoneNumber**: Represents a DID in the system inventory
  - Attributes: id (UUID), number (E.164 string), status (enum: UNASSIGNED, ALLOCATED, ASSIGNED), tenant_id (nullable UUID), provider (string), provider_metadata (JSONB), created_at, updated_at
  - Relationships: Belongs to tenant (optional), has one assignment (optional)
  - Constraints: Unique number globally, tenant_id required when status=ALLOCATED/ASSIGNED

- **DIDAssignment**: Maps a phone number to its destination
  - Attributes: id (UUID), phone_number_id (UUID FK), assigned_type (enum: USER, IVR, QUEUE, EXTERNAL), assigned_id (nullable UUID for USER/IVR/QUEUE), assigned_value (nullable string for EXTERNAL), created_at, updated_at, created_by (UUID FK to User)
  - Relationships: Belongs to PhoneNumber, references User/IVR/Queue based on assigned_type
  - Constraints: Unique phone_number_id (one active assignment per DID), assigned_id required when type=USER/IVR/QUEUE, assigned_value required when type=EXTERNAL

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Platform admin can import 1000+ DIDs via JSON in under 30 seconds with full validation
- **SC-002**: Tenant admin can assign a DID to a user in under 5 clicks with immediate validation feedback
- **SC-003**: Apply operation generates correct [from-trunk-external] dialplan for 100+ DID assignments
- **SC-004**: Incoming calls to assigned DIDs connect to correct destination within 2 seconds of Asterisk receiving INVITE
- **SC-005**: System prevents 100% of invalid assignments (duplicate DIDs, non-existent users) through validation
- **SC-006**: DID inventory UI loads and filters 5000+ numbers with pagination in under 2 seconds
- **SC-007**: RBAC correctly isolates tenant DID pools (tenant A cannot see tenant B's DIDs) in 100% of test cases
- **SC-008**: Audit logs capture all DID lifecycle events (import, allocate, assign, unassign) with actor attribution
- **SC-009**: Rollback on failed Apply correctly restores previous DID routing configuration
- **SC-010**: API documentation (OpenAPI) fully describes all DID endpoints with request/response examples

## Assumptions and Dependencies

### Assumptions
- Phone numbers are provided in E.164 international format by SIP trunk provider
- Each tenant uses a single Asterisk dialplan context (e.g., [tenant-acme])
- Incoming calls arrive with E.164 caller ID in SIP FROM header
- SIP trunk is configured to route calls to [from-trunk-external] context
- Tenant admins have already provisioned users with extensions before assigning DIDs

### Dependencies
- Existing Safe Apply workflow (Phase 4) must be operational
- User and Tenant models must exist with extension management
- Asterisk Manager Interface (AMI) integration must support dialplan reload
- Database must support JSONB for provider metadata storage
- Frontend must implement DID management UI components (list, assign, import)

### Integration Points
- **DialplanGenerator**: Extend to generate [from-trunk-external] entries alongside [tenant-X] contexts
- **ApplyService**: Include DID routing in validation and generation steps
- **User API**: Expose assigned DID(s) in user detail responses
- **Audit Logging**: Reuse existing audit_log table with DID-specific event types
