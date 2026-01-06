---
id: 007
title: Generate Implementation Tasks Breakdown
stage: tasks
date: 2026-01-05
surface: agent
model: claude-sonnet-4.5
feature: zoom-pbx-portal
branch: 001-zoom-pbx-portal
user: Ozair Tariq
command: /sp.tasks
labels: ["tasks", "implementation", "user-stories", "mvp", "parallel-execution"]
links:
  spec: specs/001-zoom-pbx-portal/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-zoom-pbx-portal/tasks.md
tests:
  - Task format validation: All 168 tasks follow strict checklist format with IDs, labels, file paths
  - User story mapping: Each task tagged with [US1]-[US8] story label for traceability
  - Parallel opportunities: 60+ tasks marked [P] for concurrent execution
  - MVP validation: Phases 1-4 (66 tasks) deliver independently testable core value
---

## Prompt

User triggered `/sp.tasks` command to generate a detailed, actionable implementation task breakdown from the planning artifacts (spec.md, plan.md, data-model.md, contracts/openapi.yaml, quickstart.md).

The `/sp.tasks` workflow requires:
1. Setup: Run `.specify/scripts/powershell/check-prerequisites.ps1 -Json` to get feature directory and available docs
2. Load design documents: spec.md (user stories with priorities), plan.md (tech stack, structure), data-model.md (entities), contracts/openapi.yaml (API endpoints), research.md (decisions)
3. Extract information: User stories (8 total: P1×3, P2×3, P3×3), entities (9 models), services (10 services), API endpoints (11 endpoint groups), migrations (7 migrations)
4. Generate tasks.md: Organize by user story for independent implementation and testing
5. Report: Total task count, MVP scope, parallel opportunities, dependencies

**Context**: No additional arguments provided - standard task generation from existing planning artifacts.

## Response snapshot

Successfully generated comprehensive implementation task breakdown with **168 tasks** organized by user story.

### Task Organization

**Phase 1: Setup (10 tasks)**
- Project initialization: Python 3.12, FastAPI, SQLAlchemy, dependencies
- Environment configuration, .gitignore, project structure
- **Purpose**: Get development environment ready

**Phase 2: Foundational (29 tasks - T011-T039) ⚠️ BLOCKING**
- Database connections (PostgreSQL + MariaDB PJSIP Realtime)
- Authentication & authorization (JWT, RBAC, 4 roles)
- Core models (Tenant, User, AuditLog, ApplyJob extensions)
- Core services (AuditService, ExtensionAllocator)
- Database migrations (007_extend_tenant_user, 006_add_audit_log)
- API infrastructure (FastAPI app, auth endpoints, health check)
- Asterisk integration (AMI client, health checker, apply service enhancements)
- Config generators (inbound, internal, outbound dialplan generators)
- **Purpose**: Build foundation that BLOCKS all user stories - must complete before ANY story work begins

**Phase 3: User Story 1 - User Provisioning (15 tasks - T040-T054) 🎯 MVP**
- Create Device model and migration
- Extend UserService, implement DeviceService
- Extend PJSIP Realtime for multi-device (unique SIP username per device, shared AOR)
- Update internal dialplan generator for extension-to-extension routing
- Create Device API endpoints with registration status
- Integrate with ApplyService for MariaDB sync
- Add validation and audit logging
- **Delivers**: Users with auto-assigned extensions, multi-device support, extension-to-extension calls

**Phase 4: User Story 3 - Safe Apply (12 tasks - T055-T066) 🎯 MVP**
- Implement ApplyValidator (extension uniqueness, DID format, destination validity, trunk reachability)
- Add pre-apply validation step
- Implement config backup and PostgreSQL advisory locks
- Add automatic rollback on reload failure
- Create ApplyJob audit records with status transitions
- Add Apply API endpoints (preview, jobs history, job details)
- **Delivers**: Safe configuration apply with validation and automatic rollback

**Phase 5: User Story 2 - Inbound DID Routing (12 tasks - T067-T078)**
- Create DID model and migration with E.164 validation
- Implement DIDService with destination validation
- Update inbound dialplan generator for DID routing
- Create DID API endpoints
- Add DID validation in ApplyValidator
- **Delivers**: External phone numbers route to correct users

**Phase 6: User Story 4 - Multi-Device Management (9 tasks - T079-T087)**
- Add device label uniqueness, enable/disable, status caching
- Implement device count limit (max 10 per user)
- Enhance status endpoint with user_agent, contact_uri, last_registration
- Update PJSIP Realtime for simultaneous ring (max_contacts=10)
- **Delivers**: Enhanced multi-device management with operational controls

**Phase 7: User Story 5 - Outbound Calling (17 tasks - T088-T104)**
- Create Trunk and OutboundPolicy models and migration
- Implement TrunkService and OutboundPolicyService
- Update outbound dialplan generator for pattern matching and trunk failover
- Add number normalization (prepend, strip transformations)
- Create Trunk and Policy API endpoints
- Link tenant.outbound_policy_id for default policy
- **Delivers**: Cost control via outbound policies with trunk failover

**Phase 8: User Story 6 - Self-Service (13 tasks - T105-T117)**
- Create migration for DND, call forwarding, voicemail fields
- Implement SelfServiceService
- Update internal dialplan generator for DND and call forwarding
- Add immediate apply for self-service (no full apply needed)
- Create self-service API endpoints (DND, forward, voicemail PIN, greeting upload)
- Implement voicemail greeting file storage
- **Delivers**: End user autonomy for phone settings

**Phase 9: User Story 7 - Tenant Management (9 tasks - T118-T126)**
- Create Tenant API endpoints (platform admin only)
- Add tenant suspension and statistics
- Update dialplan generators to check tenant.status
- Add tenant isolation validation
- Enforce platform_admin role restrictions
- **Delivers**: Multi-tenant SaaS capability with complete isolation

**Phase 10: User Story 8 - Diagnostics (9 tasks - T127-T135)**
- Enhance health check with detailed component status and latency metrics
- Add trunk/device status aggregation endpoints
- Implement real-time status updates via AMI events
- Add support role read-only access enforcement
- Create audit log query endpoint with pagination
- **Delivers**: Operational visibility for self-service troubleshooting

**Phase 11: Polish & Cross-Cutting (33 tasks - T136-T168)**
- Security hardening: HTTPS redirect, rate limiting, CORS, security headers (5 tasks)
- Performance optimization: connection pooling, pagination, indexes, caching (4 tasks)
- Error handling: structured errors, request ID tracking, logging (4 tasks)
- Frontend integration: auth, users, devices, DIDs, apply, self-service, diagnostics (7 tasks)
- Documentation: OpenAPI, seed scripts, README, systemd service (7 tasks)
- Final validation: end-to-end test, story independence, success criteria, security audit, performance test (6 tasks)
- **Delivers**: Production-ready system with security, performance, and documentation

### Task Metadata

**Total Tasks**: 168
- **MVP Tasks (Phases 1-4)**: 66 tasks
- **Full Feature Tasks (All Phases)**: 168 tasks
- **Parallel Opportunities**: 60+ tasks marked [P] for concurrent execution

**Task Format** (STRICT):
```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

Examples:
- `- [ ] T001 Create project structure per implementation plan` (Setup - no story label)
- `- [ ] T020 [P] [US1] Extend Tenant model in src/models/tenant.py` (Foundational - parallel)
- `- [ ] T040 [P] [US1] Create Device model in src/models/device.py` (US1 - parallel)
- `- [ ] T055 [US3] Implement ApplyValidator class in src/services/apply_service.py` (US3 - sequential)

**Story Labels**:
- No label: Setup, Foundational, Polish phases
- [US1]: User Provisioning (P1) - MVP core
- [US2]: Inbound DID Routing (P2)
- [US3]: Safe Apply (P1) - MVP core
- [US4]: Multi-Device Management (P2)
- [US5]: Outbound Calling (P2)
- [US6]: Self-Service (P3)
- [US7]: Tenant Management (P3)
- [US8]: Diagnostics (P3)

### Dependencies & Execution Order

**Phase Dependencies**:
```
Setup (Phase 1) → No dependencies
    ↓
Foundational (Phase 2) → Depends on Setup - BLOCKS all user stories
    ↓
┌───────────────┴───────────────┐
│                               │
US1 (Phase 3) + US3 (Phase 4)  ← MVP CORE
    ↓
┌───┴───┬───────┬───────┬───────┐
│       │       │       │       │
US2     US4     US5     US6     US7/US8
│       │       │       │       │
└───┬───┴───┬───┴───┬───┴───┬───┘
    │       │       │       │
    └───────┴───────┴───────┘
            ↓
    Polish (Phase 11)
```

**Critical Path for MVP**:
1. Phase 1: Setup → ~1 day
2. Phase 2: Foundational (BLOCKING) → ~3-4 days
3. Phase 3: US1 User Provisioning → ~3-4 days
4. Phase 4: US3 Safe Apply → ~2-3 days
5. **STOP HERE** for MVP validation (66 tasks, ~9-12 days solo)

**User Story Independence**:
- US1 (User Provisioning): Foundation for all other stories
- US3 (Safe Apply): Implemented alongside US1 for safety
- US2 (DID Routing): Independent (requires US1 for users to exist)
- US4 (Multi-Device): Extends US1
- US5 (Outbound Calling): Independent (requires US1 for users)
- US6 (Self-Service): Extends US1
- US7 (Tenant Management): Independent (extends existing tenant model)
- US8 (Diagnostics): Requires US1/US2 for devices/DIDs to diagnose

**Parallel Opportunities**:
- Setup: T003-T006, T008, T010 (6 tasks)
- Foundational: T016-T018 (auth), T020-T023 (models), T036-T038 (generators) (10 tasks)
- US1: T040 (Device model) parallel with T043 (UserService)
- US2: T067 (DID model) independent start
- US5: T088-T089 (Trunk and Policy models) parallel
- Polish: All security (5), performance (4), error (4), frontend (7), docs (7) tasks can run in parallel (27 tasks)

### Implementation Strategies

**MVP First (Phases 1-4 Only)**:
- Delivers: User provisioning, multi-device, extension calls, safe apply
- Effort: 66 tasks, ~9-12 days (1 developer) or ~5-7 days (2-3 developers)
- Value: Core PBX functionality with safety guarantees

**Incremental Delivery** (Add stories sequentially):
- Iteration 1: MVP (US1 + US3)
- Iteration 2: External Calling (US2 + US5) → +5-7 days
- Iteration 3: User Experience (US4 + US6) → +3-5 days
- Iteration 4: Scalability (US7 + US8) → +4-6 days
- Iteration 5: Production Ready (Polish) → +3-5 days
- **Total**: ~25-35 days (1 developer)

**Parallel Team** (3 developers):
- Week 1-2: MVP (all on Foundational, then split US1/US3)
- Week 3: External Calling (US2 + US5)
- Week 4: User Experience (US4 + US6)
- Week 5: Scalability (US7 + US8)
- Week 6: Polish & Launch
- **Total**: ~6 weeks (3 developers) = ~18 person-days equivalent

### Validation Results

**Format Validation**: ✅ PASS
- All 168 tasks follow strict checklist format: `- [ ] [ID] [P?] [Story?] Description`
- Task IDs sequential (T001-T168)
- 60+ tasks marked [P] for parallel execution
- 106 tasks tagged with story labels [US1]-[US8]
- All tasks include file paths

**User Story Mapping**: ✅ PASS
- Each of 8 user stories has dedicated phase with tasks
- US1 (15 tasks), US2 (12 tasks), US3 (12 tasks), US4 (9 tasks), US5 (17 tasks), US6 (13 tasks), US7 (9 tasks), US8 (9 tasks)
- Each story independently testable per spec.md
- Dependencies clearly documented

**MVP Scope**: ✅ PASS
- MVP = Phases 1-4 (Setup + Foundational + US1 + US3)
- 66 tasks deliver core value: user provisioning, multi-device, extension calls, safe apply
- Independently deployable and demonstrable

**Completeness**: ✅ PASS
- All 9 entities from data-model.md mapped to tasks (Tenant, User, Device, DID, Trunk, OutboundPolicy, ApplyJob, AuditLog, Extension)
- All 10 services from plan.md mapped to tasks
- All 11 API endpoint groups from contracts/openapi.yaml mapped to tasks
- All 7 migrations from plan.md mapped to tasks
- All 3 config generators (inbound, internal, outbound) mapped to tasks

**Tests**: ⚠️ NOT INCLUDED (as requested)
- Spec did not explicitly request TDD approach
- Test tasks can be added later if needed (unit, integration, contract tests)
- Each user story has "Independent Test" criteria in spec.md for manual validation

## Outcome

- ✅ Impact: Comprehensive implementation task breakdown created with 168 tasks organized by user story. MVP clearly defined (66 tasks, Phases 1-4). Each user story independently implementable and testable. Ready for immediate execution.
- 🧪 Tests: Format validation passed (all tasks follow checklist format), User story mapping validated (8 stories with dedicated phases), MVP scope validated (66 tasks deliver core value), Completeness validated (all entities, services, endpoints, migrations mapped)
- 📁 Files: Created tasks.md (619 lines) in specs/001-zoom-pbx-portal/
- 🔁 Next prompts: Begin implementation with Phase 1 (Setup) tasks T001-T010, or launch TodoWrite to track task progress during implementation
- 🧠 Reflection: Task generation successfully organized 168 tasks by user story for independent implementation. MVP clearly scoped to Phases 1-4 (66 tasks) enabling early validation before investing in remaining stories. Parallel opportunities identified (60+ [P] tasks) enable team collaboration. Each task follows strict format with ID, optional [P] marker, story label, and file path for LLM executability. Dependencies documented at phase, story, and task levels. Three implementation strategies provided (MVP first, incremental, parallel team) with effort estimates. Foundation phase (29 tasks) correctly identified as blocking all user stories - prevents premature story work. Story independence validated against spec.md criteria. Format validation confirms all 168 tasks are actionable and traceable. Tests intentionally omitted per spec (not explicitly requested) - can be added later if TDD adopted. Ready for immediate implementation starting with T001.

## Evaluation notes (flywheel)

- Failure modes observed: None - all tasks generated successfully. Initial attempt to use bash PHR creation script failed (script doesn't exist), fell back to manual PHR creation successfully.
- Graders run and results (PASS/FAIL):
  - Format Validation: PASS (all 168 tasks follow checklist format with IDs, labels, file paths)
  - User Story Mapping: PASS (8 stories mapped to dedicated phases with independent test criteria)
  - MVP Scope: PASS (66 tasks in Phases 1-4 deliver core value independently)
  - Completeness: PASS (all entities, services, endpoints, migrations from planning docs mapped)
  - Parallel Opportunities: PASS (60+ tasks marked [P] for concurrent execution)
- Prompt variant (if applicable): Standard /sp.tasks workflow with no additional arguments
- Next experiment (smallest change to try): When implementing tasks, consider using TodoWrite tool to track real-time progress through the 168 tasks. This would provide visibility into completion rate, blockers, and parallel execution opportunities. Could also experiment with automated task validation (e.g., checking that file paths exist after task completion, verifying migrations run successfully, ensuring endpoints appear in /docs after API tasks).
