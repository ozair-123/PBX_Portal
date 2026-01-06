# Tasks: DID Inventory & Inbound Routing Management

**Input**: Design documents from `/specs/002-did-inbound-routing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## User Story Mapping

| Story | Priority | Title | MVP |
|-------|----------|-------|-----|
| US1 | P1 | Platform Admin Imports DID Inventory | ✅ Core |
| US2 | P2 | Platform Admin Allocates DIDs to Tenant | ➖ Optional |
| US3 | P1 | Tenant Admin Assigns DID to User | ✅ Core |
| US4 | P3 | Tenant Admin Assigns DID to Voicemail | ➖ Optional |
| US5 | P1 | Safe Apply Triggers Inbound Routing Generation | ✅ Core |
| US6 | P2 | View DID Inventory with Filters | ➖ Optional |

**MVP Scope**: US1 + US3 + US5 (import → assign to user → generate dialplan)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and database migrations for DID feature

- [ ] T001 Create Alembic migration for PhoneNumber table in alembic/versions/YYYYMMDD_HHMM_add_phone_number_model.py
- [ ] T002 Create Alembic migration for DIDAssignment table in alembic/versions/YYYYMMDD_HHMM_add_did_assignment_model.py
- [ ] T003 Run database migrations with alembic upgrade head
- [ ] T004 Verify phone_numbers and did_assignments tables exist in PostgreSQL
- [ ] T005 Verify CHECK constraints and indexes are created correctly

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and schemas that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 [P] Create PhoneNumber model in src/models/phone_number.py with E.164 validation, status enum, and tenant_id FK
- [ ] T007 [P] Create DIDAssignment model in src/models/did_assignment.py with polymorphic assignment types and CHECK constraints
- [ ] T008 [P] Add PhoneNumber and DIDAssignment to src/models/__init__.py exports
- [ ] T009 [P] Create PhoneNumberStatus enum in src/models/phone_number.py (UNASSIGNED, ALLOCATED, ASSIGNED)
- [ ] T010 [P] Create AssignmentType enum in src/models/did_assignment.py (USER, IVR, QUEUE, EXTERNAL)
- [ ] T011 [P] Add phone_numbers relationship to Tenant model in src/models/tenant.py
- [ ] T012 [P] Create DIDImportItem schema in src/schemas/phone_number.py with E.164 field validation
- [ ] T013 [P] Create DIDImportRequest schema in src/schemas/phone_number.py (list of DIDImportItem, max 10000)
- [ ] T014 [P] Create DIDImportResponse schema in src/schemas/phone_number.py (imported, failed, errors fields)
- [ ] T015 [P] Create PhoneNumberResponse schema in src/schemas/phone_number.py with nested assignment
- [ ] T016 [P] Create PhoneNumberListResponse schema in src/schemas/phone_number.py with pagination
- [ ] T017 [P] Create DIDAssignmentResponse schema in src/schemas/phone_number.py
- [ ] T018 [P] Create DIDAllocateRequest schema in src/schemas/phone_number.py (tenant_id field)
- [ ] T019 [P] Create DIDAssignRequest schema in src/schemas/phone_number.py with polymorphic fields (assigned_type, assigned_id, assigned_value)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Platform Admin Imports DID Inventory (Priority: P1) 🎯 MVP

**Goal**: Enable platform admins to bulk import DIDs from carrier into global pool

**Independent Test**: Import JSON file with 100+ DIDs, verify all appear with status=UNASSIGNED in database

**Dependencies**: Phase 2 (models and schemas must exist)

### Service Layer

- [ ] T020 [US1] Create DIDService class in src/services/did_service.py with E164_REGEX constant
- [ ] T021 [US1] Implement DIDService.validate_e164() static method with regex validation
- [ ] T022 [US1] Implement DIDService.import_dids() static method with transaction rollback on validation errors
- [ ] T023 [US1] Add E.164 validation loop in import_dids() to collect errors
- [ ] T024 [US1] Add duplicate number check in import_dids() using session.query()
- [ ] T025 [US1] Add PhoneNumber creation loop with UNASSIGNED status
- [ ] T026 [US1] Add audit logging via AuditService.log_create() for bulk import operation
- [ ] T027 [US1] Add exception handling with session.rollback() and RuntimeError

### API Layer

- [ ] T028 [US1] Create DIDs router in src/api/v1/dids.py with APIRouter()
- [ ] T029 [US1] Implement POST /dids/import endpoint with require_role("platform_admin") dependency
- [ ] T030 [US1] Add DIDImportRequest parsing and DIDService.import_dids() call in import endpoint
- [ ] T031 [US1] Add error handling for ValueError (400) and RuntimeError (500) in import endpoint
- [ ] T032 [US1] Add source_ip and user_agent extraction from Request in import endpoint
- [ ] T033 [US1] Register DIDs router in src/api/v1/__init__.py with prefix="/dids" and tags=["DIDs"]

### Verification

- [ ] T034 [US1] Test E.164 validation with valid numbers (+15551234567, +442071234567, +8613800138000)
- [ ] T035 [US1] Test E.164 validation rejects invalid formats (no +, leading zero, too long)
- [ ] T036 [US1] Test bulk import with 500 DIDs completes successfully
- [ ] T037 [US1] Test duplicate number detection returns errors without creating records
- [ ] T038 [US1] Test partial validation errors trigger full rollback
- [ ] T039 [US1] Verify audit log entry created for import operation with actor_id
- [ ] T040 [US1] Test API endpoint returns 403 for non-platform_admin users

**Story Complete**: ✅ Platform admins can import DIDs from carriers

---

## Phase 4: User Story 2 - Platform Admin Allocates DIDs to Tenant (Priority: P2)

**Goal**: Enable platform admins to allocate DIDs from global pool to specific tenants

**Independent Test**: Allocate 10 DIDs to tenant, verify tenant admin can see them and other tenants cannot

**Dependencies**: Phase 3 (US1 must be complete to have DIDs in system)

### Service Layer

- [ ] T041 [US2] Implement DIDService.allocate_to_tenant() static method
- [ ] T042 [US2] Add PhoneNumber status check (must be UNASSIGNED) in allocate_to_tenant()
- [ ] T043 [US2] Add status transition UNASSIGNED → ALLOCATED with tenant_id assignment
- [ ] T044 [US2] Add before/after state capture via AuditService.entity_to_dict()
- [ ] T045 [US2] Add audit logging via AuditService.log_update() for allocation
- [ ] T046 [US2] Implement DIDService.deallocate() static method for ALLOCATED → UNASSIGNED transition
- [ ] T047 [US2] Add validation in deallocate() to prevent deallocating ASSIGNED DIDs

### API Layer

- [ ] T048 [US2] Implement PATCH /dids/{did_id}/allocate endpoint with require_role("platform_admin")
- [ ] T049 [US2] Add DIDAllocateRequest parsing and DIDService.allocate_to_tenant() call
- [ ] T050 [US2] Add error handling for ValueError (400), NotFoundException (404)
- [ ] T051 [US2] Implement PATCH /dids/{did_id}/deallocate endpoint with require_role("platform_admin")
- [ ] T052 [US2] Add DIDService.deallocate() call with error handling

### Verification

- [ ] T053 [US2] Test allocating UNASSIGNED DID to tenant changes status to ALLOCATED
- [ ] T054 [US2] Test allocating already ALLOCATED DID returns 400 error
- [ ] T055 [US2] Test deallocating ALLOCATED DID returns to UNASSIGNED with tenant_id=NULL
- [ ] T056 [US2] Test deallocating ASSIGNED DID returns 400 error
- [ ] T057 [US2] Verify audit log captures tenant_id change
- [ ] T058 [US2] Test API endpoints return 403 for non-platform_admin users

**Story Complete**: ✅ Platform admins can allocate DIDs to tenants

---

## Phase 5: User Story 3 - Tenant Admin Assigns DID to User (Priority: P1) 🎯 MVP

**Goal**: Enable tenant admins to assign DIDs to users for inbound call routing

**Independent Test**: Assign DID to user, verify assignment record created and user/DID relationship established

**Dependencies**: Phase 3 (US1) OR Phase 4 (US2) - needs DIDs allocated to tenant

### Service Layer

- [ ] T059 [US3] Implement DIDService.assign_to_destination() static method
- [ ] T060 [US3] Add PhoneNumber status check (must be ALLOCATED) in assign_to_destination()
- [ ] T061 [US3] Add assignment type validation (USER requires assigned_id, EXTERNAL requires assigned_value)
- [ ] T062 [US3] Add User existence check and tenant match validation for USER type
- [ ] T063 [US3] Add DIDAssignment creation with phone_number_id UNIQUE constraint handling
- [ ] T064 [US3] Add PhoneNumber status transition ALLOCATED → ASSIGNED
- [ ] T065 [US3] Add audit logging via AuditService.log_create() for assignment
- [ ] T066 [US3] Add IntegrityError handling for duplicate assignments (409 Conflict)
- [ ] T067 [US3] Implement DIDService.unassign() static method
- [ ] T068 [US3] Add DIDAssignment deletion and status transition ASSIGNED → ALLOCATED in unassign()
- [ ] T069 [US3] Add audit logging via AuditService.log_delete() for unassignment

### API Layer

- [ ] T070 [US3] Implement POST /dids/{did_id}/assign endpoint with require_role("tenant_admin")
- [ ] T071 [US3] Add DIDAssignRequest parsing with assigned_type field validation
- [ ] T072 [US3] Add tenant_id check (tenant admin can only assign DIDs in their tenant)
- [ ] T073 [US3] Add DIDService.assign_to_destination() call with AssignmentType enum conversion
- [ ] T074 [US3] Add error handling for ValueError (400), IntegrityError (409), NotFoundException (404)
- [ ] T075 [US3] Implement DELETE /dids/{did_id}/assign endpoint with require_role("tenant_admin")
- [ ] T076 [US3] Add tenant_id check for unassignment authorization
- [ ] T077 [US3] Add DIDService.unassign() call with error handling

### Verification

- [ ] T078 [US3] Test assigning ALLOCATED DID to user creates DIDAssignment with assigned_type=USER
- [ ] T079 [US3] Test assigning user from different tenant returns 400 error
- [ ] T080 [US3] Test assigning already ASSIGNED DID returns 409 Conflict
- [ ] T081 [US3] Test assigning non-existent user returns 400 error
- [ ] T082 [US3] Test unassigning DID deletes assignment and returns status to ALLOCATED
- [ ] T083 [US3] Test tenant admin cannot assign DIDs from other tenants (403)
- [ ] T084 [US3] Verify audit log captures assignment creation and deletion
- [ ] T085 [US3] Test PhoneNumber status transitions correctly (ALLOCATED → ASSIGNED → ALLOCATED)

**Story Complete**: ✅ Tenant admins can assign DIDs to users

---

## Phase 6: User Story 4 - Tenant Admin Assigns DID to Voicemail (Priority: P3)

**Goal**: Enable tenant admins to assign DIDs to voicemail boxes using EXTERNAL type

**Independent Test**: Assign DID with assigned_type=EXTERNAL and assigned_value="VoiceMail(2000@tenant-acme)", verify assignment created

**Dependencies**: Phase 5 (US3) - reuses same service methods, just different assignment type

### Service Layer

- [ ] T086 [US4] Add EXTERNAL type validation in DIDService.assign_to_destination() (already implemented if polymorphic logic done in US3)
- [ ] T087 [US4] Verify assigned_value required and assigned_id must be NULL for EXTERNAL type

### API Layer

- [ ] T088 [US4] Test POST /dids/{did_id}/assign endpoint with assigned_type=EXTERNAL payload
- [ ] T089 [US4] Verify DIDAssignRequest schema accepts assigned_value field

### Verification

- [ ] T090 [US4] Test assigning DID to voicemail with assigned_value="VoiceMail(2000@tenant-acme)"
- [ ] T091 [US4] Test assigning EXTERNAL type without assigned_value returns 400 error
- [ ] T092 [US4] Test assigning EXTERNAL type with assigned_id returns 400 error (field consistency validation)
- [ ] T093 [US4] Verify audit log captures EXTERNAL assignment

**Story Complete**: ✅ Tenant admins can assign DIDs to voicemail boxes

---

## Phase 7: User Story 5 - Safe Apply Triggers Inbound Routing Generation (Priority: P1) 🎯 MVP

**Goal**: Generate Asterisk dialplan with [from-trunk-external] context when Apply is triggered

**Independent Test**: Create 3 DID assignments, trigger Apply, verify extensions_custom.conf contains correct routing

**Dependencies**: Phase 5 (US3) - needs DID assignments to exist

### Configuration Generation

- [ ] T094 [P] [US5] Extend InboundRouter.generate() in src/config_generator/inbound_router.py to accept did_assignments parameter
- [ ] T095 [US5] Add [from-trunk-external] context generation with header comments
- [ ] T096 [US5] Add USER type routing logic: exten => +NUMBER,1,Goto(tenant-context,extension,1)
- [ ] T097 [US5] Add EXTERNAL type routing logic: exten => +NUMBER,1,{assigned_value}
- [ ] T098 [US5] Add user lookup by assigned_id to find extension and tenant_context
- [ ] T099 [US5] Add empty context handling when no DID assignments exist

### Apply Service Integration

- [ ] T100 [US5] Extend DialplanGenerator.generate_config() in src/config_generator/dialplan_generator.py to accept did_assignments parameter
- [ ] T101 [US5] Add InboundRouter.generate() call with did_assignments in DialplanGenerator
- [ ] T102 [US5] Extend ApplyService.apply_configuration_safe() in src/services/apply_service_enhanced.py to query DIDAssignment table
- [ ] T103 [US5] Add DIDAssignment join with PhoneNumber to load assignments
- [ ] T104 [US5] Convert DIDAssignment ORM objects to dict format for DialplanGenerator
- [ ] T105 [US5] Add did_assignments_data to DialplanGenerator.generate_config() call
- [ ] T106 [US5] Verify existing backup/rollback logic handles DID routing changes

### Verification

- [ ] T107 [US5] Test InboundRouter.generate() with 1 USER assignment generates correct exten line
- [ ] T108 [US5] Test InboundRouter.generate() with 1 EXTERNAL assignment generates correct exten line
- [ ] T109 [US5] Test InboundRouter.generate() with no assignments generates empty [from-trunk-external] context
- [ ] T110 [US5] Test DialplanGenerator includes [from-trunk-external] before tenant contexts
- [ ] T111 [US5] Test Apply operation with 3 DID assignments writes correct dialplan to extensions_custom.conf
- [ ] T112 [US5] Test Apply operation with no DIDs does not error
- [ ] T113 [US5] Test Apply failure rollback restores previous dialplan with old DID routing
- [ ] T114 [US5] Verify ApplyJob audit log captures DID assignments in diff_summary

**Story Complete**: ✅ Apply generates inbound DID routing dialplan

---

## Phase 8: User Story 6 - View DID Inventory with Filters (Priority: P2)

**Goal**: Enable admins to list, filter, and search DIDs with pagination

**Independent Test**: Query API with filters (status, tenant_id, partial number search), verify results match criteria

**Dependencies**: Phase 3 (US1) - needs DIDs in database to query

### Service Layer

- [ ] T115 [P] [US6] Implement DIDService.list_dids() static method with filtering parameters
- [ ] T116 [US6] Add status filter (UNASSIGNED, ALLOCATED, ASSIGNED) in list_dids()
- [ ] T117 [US6] Add tenant_id filter for platform admin queries
- [ ] T118 [US6] Add partial number search using LIKE %pattern%
- [ ] T119 [US6] Add pagination with offset and limit
- [ ] T120 [US6] Add total count query for pagination metadata
- [ ] T121 [US6] Add eager loading of DIDAssignment relationship using joinedload()
- [ ] T122 [P] [US6] Implement DIDService.get_did() static method for single DID retrieval

### API Layer

- [ ] T123 [US6] Implement GET /dids endpoint with require_role("support") dependency
- [ ] T124 [US6] Add query parameters: status, tenant_id, number, page, page_size
- [ ] T125 [US6] Add automatic tenant_id filter for tenant_admin role (current_user.tenant_id)
- [ ] T126 [US6] Add DIDService.list_dids() call with query parameters
- [ ] T127 [US6] Return PhoneNumberListResponse with pagination metadata
- [ ] T128 [US6] Implement GET /dids/{did_id} endpoint with require_role("support")
- [ ] T129 [US6] Add tenant_id authorization check for tenant_admin role
- [ ] T130 [US6] Add DIDService.get_did() call with error handling (404)

### Verification

- [ ] T131 [US6] Test GET /dids returns all DIDs for platform_admin
- [ ] T132 [US6] Test GET /dids filters by status=UNASSIGNED correctly
- [ ] T133 [US6] Test GET /dids filters by tenant_id correctly
- [ ] T134 [US6] Test GET /dids partial number search finds "+555" in "+15551234567"
- [ ] T135 [US6] Test GET /dids pagination returns correct page and total count
- [ ] T136 [US6] Test GET /dids auto-filters for tenant_admin to their tenant only
- [ ] T137 [US6] Test GET /dids/{id} returns DID with nested assignment
- [ ] T138 [US6] Test GET /dids/{id} returns 403 for tenant_admin accessing other tenant's DID
- [ ] T139 [US6] Test GET /dids/{id} returns 404 for non-existent DID
- [ ] T140 [US6] Verify list endpoint includes eager-loaded assignment relationship (no N+1 queries)

**Story Complete**: ✅ Admins can view and filter DID inventory

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, performance optimization, documentation

### Integration Testing

- [ ] T141 [P] Create integration test for full DID lifecycle: import → allocate → assign → apply → unassign
- [ ] T142 [P] Create integration test for concurrent assignment attempts (verify unique constraint prevents race)
- [ ] T143 [P] Create integration test for multi-tenant isolation (tenant A cannot access tenant B's DIDs)

### Performance Validation

- [ ] T144 [P] Test bulk import of 1000 DIDs completes in <30 seconds
- [ ] T145 [P] Test DID assignment API response time <500ms p95 (run 100 sequential requests)
- [ ] T146 [P] Test list endpoint with 5000 DIDs returns in <2 seconds with pagination
- [ ] T147 [P] Test dialplan generation with 100+ assignments completes in <5 seconds

### Error Scenarios

- [ ] T148 [P] Test user deletion when DID assigned (verify FK constraint handling)
- [ ] T149 [P] Test tenant deletion when DIDs allocated (verify FK ON DELETE SET NULL)
- [ ] T150 [P] Test Apply failure rollback with DID assignments (verify dialplan restore)

### Documentation

- [ ] T151 [P] Verify OpenAPI docs at /docs include all DID endpoints
- [ ] T152 [P] Verify all Pydantic schemas have descriptions and examples
- [ ] T153 [P] Add docstrings to all DIDService methods
- [ ] T154 [P] Verify quickstart.md examples work (run through developer guide)

### Security & RBAC

- [ ] T155 [P] Verify all DID endpoints enforce RBAC correctly (platform_admin, tenant_admin, support, end_user)
- [ ] T156 [P] Verify tenant_id filtering prevents cross-tenant access
- [ ] T157 [P] Verify audit logs capture all DID operations with actor_id
- [ ] T158 [P] Test SQL injection attempts on number search (verify parameterized queries)

### Final Validation

- [ ] T159 Run alembic check to verify migrations are clean
- [ ] T160 Run pytest with coverage report (target >80% for new code)
- [ ] T161 Verify Constitution compliance (8 principles checklist)
- [ ] T162 Test manual Apply operation end-to-end (import → assign → apply → verify dialplan → test call routing)

---

## Dependencies & Execution Strategy

### Dependency Graph (Story Completion Order)

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
┌─────────────────┬──────────────────┬──────────────────┐
│  Phase 3 (US1)  │  Phase 4 (US2)   │   Phase 8 (US6)  │
│  Import DIDs    │  Allocate DIDs   │   View/Filter    │
│                 │                  │                  │
└────────┬────────┴─────────┬────────┴──────────────────┘
         │                  │
         │     Phase 5 (US3) ← DEPENDS ON US1 OR US2
         │     Assign to User
         │            ↓
         │     Phase 6 (US4)
         │     Assign to Voicemail
         │            ↓
         └────→ Phase 7 (US5) ← DEPENDS ON US3
                Generate Dialplan
                     ↓
              Phase 9 (Polish)
```

**Critical Path**: Phase 1 → Phase 2 → Phase 3 (US1) → Phase 5 (US3) → Phase 7 (US5) → Phase 9

**Parallelizable After Phase 2**:
- US1 (Import), US2 (Allocate), US6 (View) can be developed in parallel
- US3 can start once either US1 or US2 is complete (needs DIDs in system)
- US4 can start once US3 is complete (reuses same service methods)

### Parallel Execution Examples

**After Phase 2 Foundation**:
```bash
# Team A: Import DIDs (US1)
git checkout -b feature/did-import
# Implement T020-T040

# Team B: View/Filter (US6) - independent
git checkout -b feature/did-list
# Implement T115-T140

# Team C: Allocate to Tenant (US2) - independent
git checkout -b feature/did-allocate
# Implement T041-T058
```

**After US1 Complete**:
```bash
# Team A: Assign to User (US3) - depends on US1
git checkout -b feature/did-assign
# Implement T059-T085

# Team B: Continue US2 or US6 work
```

**After US3 Complete**:
```bash
# Team A: Dialplan Generation (US5) - depends on US3
git checkout -b feature/did-dialplan
# Implement T094-T114

# Team B: Voicemail Assignment (US4) - depends on US3
git checkout -b feature/did-voicemail
# Implement T086-T093
```

### MVP Implementation Order

**Minimum Viable Product** (deliver core inbound routing):

1. **Phase 1**: Setup (T001-T005) - 1 day
2. **Phase 2**: Foundation (T006-T019) - 2 days
3. **Phase 3**: Import DIDs (T020-T040) - 3 days
4. **Phase 5**: Assign to User (T059-T085) - 3 days
5. **Phase 7**: Generate Dialplan (T094-T114) - 2 days
6. **Phase 9**: Core tests (T141, T150, T162) - 1 day

**Total MVP**: ~12 days (US1 + US3 + US5 + critical tests)

**Post-MVP Enhancements**:
- Phase 4 (US2): Multi-tenant delegation
- Phase 6 (US4): Voicemail routing
- Phase 8 (US6): Advanced filtering
- Phase 9: Full polish (performance, security, docs)

---

## Task Summary

**Total Tasks**: 162
- **Setup**: 5 tasks (T001-T005)
- **Foundation**: 14 tasks (T006-T019)
- **US1 (Import)**: 21 tasks (T020-T040)
- **US2 (Allocate)**: 18 tasks (T041-T058)
- **US3 (Assign User)**: 27 tasks (T059-T085)
- **US4 (Assign Voicemail)**: 8 tasks (T086-T093)
- **US5 (Dialplan)**: 21 tasks (T094-T114)
- **US6 (View/Filter)**: 26 tasks (T115-T140)
- **Polish**: 22 tasks (T141-T162)

**Parallelizable Tasks**: 45 tasks marked with [P]

**Story Distribution**:
- P1 Stories: US1 (21), US3 (27), US5 (21) = 69 tasks
- P2 Stories: US2 (18), US6 (26) = 44 tasks
- P3 Stories: US4 (8) = 8 tasks

**Independent Test Criteria**:
- ✅ US1: Import 100+ DIDs, verify UNASSIGNED status
- ✅ US2: Allocate DIDs, verify tenant isolation
- ✅ US3: Assign to user, verify assignment record
- ✅ US4: Assign to voicemail, verify EXTERNAL type
- ✅ US5: Trigger Apply, verify dialplan contains routing
- ✅ US6: Query with filters, verify results match criteria

---

**Tasks Status**: ✅ Ready for implementation
**Organization**: By user story (enables independent delivery)
**Format**: ✅ All tasks follow checklist format with IDs, story labels, and file paths
**MVP Scope**: US1 + US3 + US5 (69 tasks, ~12 days)
