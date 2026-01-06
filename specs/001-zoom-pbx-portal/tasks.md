# Tasks: Zoom-Style PBX Management Portal

**Input**: Design documents from `/specs/001-zoom-pbx-portal/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Tests are NOT included in this task list as they were not explicitly requested in the feature specification. Test tasks can be added later if TDD approach is adopted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `src/`, `tests/`, `alembic/` at repository root
- Asterisk configs: `/etc/asterisk/extensions.d/synergycall/`
- Frontend: `static/` (already exists)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and basic tooling

- [ ] T001 Verify Python 3.12+ installation and create virtual environment
- [ ] T002 Install core dependencies: FastAPI 0.104+, SQLAlchemy 2.0+, uvicorn, pydantic 2.4+
- [ ] T003 [P] Install database drivers: psycopg2-binary 2.9+, mysql-connector-python 8.0+
- [ ] T004 [P] Install security dependencies: passlib[bcrypt], argon2-cffi, cryptography 41.0.7, python-jose[cryptography]
- [ ] T005 [P] Install testing dependencies: pytest 7.4+, pytest-asyncio 0.21+, httpx 0.25.2
- [ ] T006 [P] Install migration tool: alembic 1.12.1
- [ ] T007 Create `.env.example` template with all required environment variables
- [ ] T008 [P] Setup `.gitignore` to exclude `.env`, `__pycache__/`, `venv/`, `.pytest_cache/`
- [ ] T009 Create `requirements.txt` with all dependencies and pinned versions
- [ ] T010 [P] Configure project structure: ensure `src/`, `tests/`, `alembic/`, `static/` directories exist

**Checkpoint**: Project dependencies and structure ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database & Configuration

- [ ] T011 Setup PostgreSQL database connection in `src/database.py` using SQLAlchemy engine
- [ ] T012 Setup MariaDB connection in `src/mariadb_connection.py` for PJSIP Realtime
- [ ] T013 Configure environment settings in `src/config.py` using pydantic-settings
- [ ] T014 Setup structured logging in `src/logging_config.py` with JSON format support
- [ ] T015 Initialize Alembic for database migrations in `alembic/env.py`

### Authentication & Authorization

- [ ] T016 [P] Implement password hashing utilities in `src/auth/password.py` (Argon2/bcrypt)
- [ ] T017 [P] Implement JWT token generation/validation in `src/auth/jwt.py`
- [ ] T018 [P] Implement RBAC decorators in `src/auth/rbac.py` for 4 roles (platform_admin, tenant_admin, support, end_user)
- [ ] T019 Create authentication middleware in `src/middleware/auth.py` for JWT verification

### Core Models (Foundation)

- [ ] T020 [P] Extend Tenant model in `src/models/tenant.py` with ext_min, ext_max, ext_next, default_inbound_destination, outbound_policy_id, status fields
- [ ] T021 [P] Extend User model in `src/models/user.py` with role, status, outbound_callerid, voicemail_enabled, voicemail_pin_hash, dnd_enabled, call_forward_destination fields
- [ ] T022 Create AuditLog model in `src/models/audit_log.py` with actor_id, action, entity_type, entity_id, before_json, after_json, timestamp, source_ip fields
- [ ] T023 Create ApplyJob model in `src/models/apply_audit_log.py` (extend existing) with status, started_at, ended_at, error_text, diff_summary, config_files_json fields

### Core Services (Foundation)

- [ ] T024 Implement centralized audit logging service in `src/services/audit_service.py` for all CRUD operations
- [ ] T025 Extend extension allocator in `src/services/extension_allocator.py` to handle tenant.ext_next pointer with row-level locking

### Database Migrations (Foundation)

- [ ] T026 Create migration `alembic/versions/007_extend_tenant_user.py` to add new fields to tenants and users tables
- [ ] T027 Create migration `alembic/versions/006_add_audit_log.py` to create audit_logs table
- [ ] T028 Run migrations: `alembic upgrade head` to apply foundational schema changes

### API Infrastructure

- [ ] T029 Setup FastAPI app in `src/main.py` with CORS, middleware, authentication, error handlers
- [ ] T030 Create API router structure with `/api/v1` prefix
- [ ] T031 [P] Implement authentication endpoints in `src/api/auth.py`: POST /auth/login, POST /auth/refresh, POST /auth/logout
- [ ] T032 Create health check endpoint in `src/api/diagnostics.py`: GET /health (database, mariadb, asterisk_ami, disk_space checks)

### Asterisk Integration (Foundation)

- [ ] T033 Implement AMI client in `src/asterisk/ami_client.py` with persistent connection, reconnect logic, and status query methods
- [ ] T034 Implement health checker in `src/asterisk/health_checker.py` for Asterisk running status, DB connectivity, disk space
- [ ] T035 Extend apply service in `src/services/apply_service.py` with pre-apply validation phase and enhanced rollback logic

### Config Generation (Foundation)

- [ ] T036 [P] Create inbound DID routing generator in `src/config_generator/inbound_generator.py` for `generated_inbound.conf`
- [ ] T037 [P] Create internal extension-to-extension generator in `src/config_generator/internal_generator.py` for `generated_internal.conf`
- [ ] T038 [P] Create outbound policy enforcement generator in `src/config_generator/outbound_generator.py` for `generated_outbound.conf`
- [ ] T039 Refactor existing `src/config_generator/dialplan_generator.py` to delegate to inbound/internal/outbound generators

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - User Provisioning with Auto-Extension Assignment (Priority: P1) 🎯 MVP

**Goal**: Enable tenant admins to create users with auto-assigned extensions and SIP credentials so new employees can immediately register desk phones

**Independent Test**: Create user through admin portal → verify auto-assigned extension → register SIP device → make extension-to-extension call

### Implementation for User Story 1

- [ ] T040 [P] [US1] Create Device model in `src/models/device.py` with user_id, tenant_id, label, sip_username, sip_password_encrypted, transport, nat_flags_json, codecs_json, enabled fields
- [ ] T041 [US1] Create migration `alembic/versions/002_add_devices.py` to create devices table with foreign keys and unique constraints
- [ ] T042 [US1] Run migration: `alembic upgrade head` to apply devices table
- [ ] T043 [US1] Extend UserService in `src/services/user_service.py` with soft-delete, suspend, and voicemail box creation logic
- [ ] T044 [US1] Implement DeviceService in `src/services/device_service.py` with CRUD operations, SIP password encryption (Fernet), and unique username generation
- [ ] T045 [US1] Extend PJSIP Realtime service in `src/services/pjsip_realtime_service.py` to support multi-device (unique SIP username per device, shared AOR)
- [ ] T046 [US1] Update internal dialplan generator in `src/config_generator/internal_generator.py` to generate extension-to-extension routing for all active users
- [ ] T047 [US1] Extend User API endpoints in `src/api/users.py`: add PATCH /users/{user_id} for status updates, DELETE for soft-delete
- [ ] T048 [US1] Create Device API endpoints in `src/api/devices.py`: GET/POST /devices, GET/PATCH/DELETE /devices/{device_id}
- [ ] T049 [US1] Integrate DeviceService with ApplyService to sync device credentials to MariaDB ps_endpoints, ps_auths, ps_aors on apply
- [ ] T050 [US1] Add device registration status query in DeviceService using AMI client: `GET /devices/{device_id}/status`
- [ ] T051 [US1] Update ApplyService to call internal_generator for extension-to-extension dialplan on apply
- [ ] T052 [US1] Add validation in UserService: ensure extension is within tenant ext_min/ext_max range, check for duplicates
- [ ] T053 [US1] Add audit logging to UserService and DeviceService for all CREATE/UPDATE/DELETE operations
- [ ] T054 [US1] Test end-to-end: Create user via API → Create device → Apply → Verify device can register → Test extension-to-extension call

**Checkpoint**: User Story 1 complete - Users can be provisioned with extensions, devices can register, extension-to-extension calls work

---

## Phase 4: User Story 3 - Safe Configuration Apply with Rollback (Priority: P1)

**Goal**: Enable tenant admins to safely apply pending changes to Asterisk with automatic rollback on failure to prevent phone system downtime

**Independent Test**: Make changes in portal → Click Apply → Verify Asterisk reloads without downtime → Introduce invalid config → Verify automatic rollback

**Note**: This is implemented alongside US1 but extracted here for clarity

### Implementation for User Story 3

- [ ] T055 [US3] Implement ApplyValidator class in `src/services/apply_service.py` with validation checks: extension uniqueness, DID format, destination validity, trunk reachability, SIP username conflicts
- [ ] T056 [US3] Add pre-apply validation step in ApplyService: run ApplyValidator before generating configs
- [ ] T057 [US3] Implement config backup mechanism in ApplyService: copy current config files to backup directory with timestamp
- [ ] T058 [US3] Add PostgreSQL advisory lock acquisition in ApplyService to prevent concurrent applies
- [ ] T059 [US3] Implement automatic rollback in ApplyService: if reload fails, restore backup configs and reload again
- [ ] T060 [US3] Create ApplyJob audit record on every apply attempt with status transitions (PENDING → RUNNING → SUCCESS/FAILED/ROLLED_BACK)
- [ ] T061 [US3] Add Apply API endpoint: POST /apply/preview to show pending changes and validation errors without applying
- [ ] T062 [US3] Add Apply API endpoint: GET /apply/jobs to list apply history with filtering by status
- [ ] T063 [US3] Add Apply API endpoint: GET /apply/jobs/{job_id} to get detailed apply job with error messages and file diff
- [ ] T064 [US3] Update ApplyService to record config_files_json (list of files written) in ApplyJob for rollback reference
- [ ] T065 [US3] Add error handling in ApplyService: catch AMI connection errors, dialplan syntax errors, reload failures
- [ ] T066 [US3] Test apply workflow: Valid changes → Apply succeeds, Invalid changes → Validation fails, Reload failure → Rollback completes

**Checkpoint**: User Story 3 complete - Apply workflow is safe with validation and automatic rollback

---

## Phase 5: User Story 2 - Inbound DID Routing to Users (Priority: P2)

**Goal**: Enable tenant admins to assign external phone numbers (DIDs) to users so incoming calls from public network reach correct employee

**Independent Test**: Assign DID to user → Make external call to DID → Verify user's device rings → Reassign DID → Verify new user receives calls

### Implementation for User Story 2

- [ ] T067 [P] [US2] Create DID model in `src/models/did.py` with tenant_id, did_number, label, provider, destination_type (enum: USER, RING_GROUP, IVR, QUEUE, VOICEMAIL, EXTERNAL), destination_target, enabled fields
- [ ] T068 [US2] Create migration `alembic/versions/003_add_dids.py` to create dids table with E.164 format check constraint, unique did_number
- [ ] T069 [US2] Run migration: `alembic upgrade head` to apply dids table
- [ ] T070 [US2] Implement DIDService in `src/services/did_service.py` with CRUD operations, E.164 validation, destination validation (check user exists if type=USER)
- [ ] T071 [US2] Update inbound dialplan generator in `src/config_generator/inbound_generator.py` to generate DID routing entries from dids table
- [ ] T072 [US2] Add logic in inbound_generator to route unassigned DIDs to tenant.default_inbound_destination
- [ ] T073 [US2] Create DID API endpoints in `src/api/dids.py`: GET/POST /dids, GET/PATCH/DELETE /dids/{did_id}
- [ ] T074 [US2] Add DID reassignment validation in DIDService: allow changing destination_target, update dialplan on apply
- [ ] T075 [US2] Update ApplyService to call inbound_generator for DID routing dialplan on apply
- [ ] T076 [US2] Add DID validation in ApplyValidator: check E.164 format, validate destination exists, detect duplicate DIDs
- [ ] T077 [US2] Add audit logging to DIDService for all CREATE/UPDATE/DELETE operations
- [ ] T078 [US2] Test DID routing: Assign DID to user → Apply → Verify inbound call routes correctly → Reassign → Verify new routing

**Checkpoint**: User Story 2 complete - DIDs can be assigned to users, inbound calls route correctly

---

## Phase 6: User Story 4 - Device Management for Multi-Device Users (Priority: P2)

**Goal**: Enable tenant admins to allow users to have multiple SIP devices (desk phone, softphone, mobile) for work flexibility

**Independent Test**: Create multiple devices for one user → Register both devices → Call user's extension → Verify both devices ring simultaneously

**Note**: Core multi-device support is already implemented in US1 (T040-T050). This phase adds management enhancements.

### Implementation for User Story 4

- [ ] T079 [US4] Add device label uniqueness validation in DeviceService: prevent duplicate labels per user (e.g., user can't have two "Desk Phone" devices)
- [ ] T080 [US4] Implement device enable/disable in DeviceService: allow disabling device without deleting (blocks SIP registration)
- [ ] T081 [US4] Add device status query caching in DeviceService: cache AMI status responses for 30 seconds to reduce AMI load
- [ ] T082 [US4] Update Device API: add filtering by user_id, enabled status in GET /devices endpoint
- [ ] T083 [US4] Add device count limit validation in DeviceService: enforce max 10 devices per user (prevent abuse)
- [ ] T084 [US4] Enhance device status endpoint to show user_agent, contact_uri, last_registration timestamp from AMI
- [ ] T085 [US4] Update PJSIP Realtime sync to set max_contacts=10 on shared AOR for simultaneous ring
- [ ] T086 [US4] Add device deletion cleanup: remove ps_endpoints, ps_auths entries from MariaDB on device delete
- [ ] T087 [US4] Test multi-device: Create 3 devices for one user → Register all → Call extension → Verify all ring → Delete one device → Verify only remaining devices ring

**Checkpoint**: User Story 4 complete - Multi-device management works with status tracking and simultaneous ring

---

## Phase 7: User Story 5 - Outbound Calling with Policy Enforcement (Priority: P2)

**Goal**: Enable tenant admins to control which users can make international/premium calls and route outbound calls through configured trunks for cost control

**Independent Test**: Configure "Local Only" policy → Assign to user → User dials international number → Verify call blocked → User dials local number → Verify call routes through trunk

### Implementation for User Story 5

- [ ] T088 [P] [US5] Create Trunk model in `src/models/trunk.py` with tenant_id (nullable for global), name, host, auth_mode (enum: registration, ip_auth), registration_string, transport, codecs_json, enabled fields
- [ ] T089 [P] [US5] Create OutboundPolicy model in `src/models/outbound_policy.py` with tenant_id, name, rules_json (patterns, transformations, trunk_priority), enabled fields
- [ ] T090 [US5] Create migration `alembic/versions/004_add_trunks_policies.py` to create trunks and outbound_policies tables
- [ ] T091 [US5] Run migration: `alembic upgrade head` to apply trunks and policies tables
- [ ] T092 [US5] Implement TrunkService in `src/services/trunk_service.py` with CRUD operations, trunk status query via AMI (registration status)
- [ ] T093 [US5] Implement OutboundPolicyService in `src/services/outbound_policy_service.py` with CRUD operations, regex pattern validation, trunk reference validation
- [ ] T094 [US5] Update outbound dialplan generator in `src/config_generator/outbound_generator.py` to generate pattern matching and trunk routing from outbound_policies table
- [ ] T095 [US5] Add trunk failover logic in outbound_generator: prioritize trunks by trunk_priority array, generate Dial() with sequential fallback
- [ ] T096 [US5] Add number normalization in outbound_generator: apply transformations (prepend, strip) from policy rules
- [ ] T097 [US5] Create Trunk API endpoints in `src/api/trunks.py`: GET/POST /trunks, GET/PATCH/DELETE /trunks/{trunk_id}, GET /trunks/{trunk_id}/status
- [ ] T098 [US5] Create OutboundPolicy API endpoints in `src/api/outbound_policies.py`: GET/POST /outbound-policies, GET/PATCH/DELETE /outbound-policies/{policy_id}
- [ ] T099 [US5] Update ApplyService to call outbound_generator for policy enforcement dialplan on apply
- [ ] T100 [US5] Add policy validation in ApplyValidator: validate regex patterns compile, check trunk UUIDs exist and are enabled
- [ ] T101 [US5] Add default blocking logic in outbound_generator: if no pattern matches, block call with Playback(ss-noservice)
- [ ] T102 [US5] Add audit logging to TrunkService and OutboundPolicyService for all CREATE/UPDATE/DELETE operations
- [ ] T103 [US5] Link tenant.outbound_policy_id to default policy: update outbound_generator to use tenant's default policy if user has no override
- [ ] T104 [US5] Test outbound policy: Create policy "Local Only" → Create trunk → Assign to tenant → User dials local number → Allowed, User dials international → Blocked

**Checkpoint**: User Story 5 complete - Outbound calling controlled by policies with trunk failover

---

## Phase 8: User Story 6 - End User Self-Service Features (Priority: P3)

**Goal**: Enable end users to control their own phone settings (DND, call forwarding, voicemail PIN) without contacting IT for user autonomy

**Independent Test**: Login as end user → Enable DND → Incoming call goes to voicemail → Set call forward → Incoming call rings forwarded number → Change voicemail PIN → Verify new PIN works

### Implementation for User Story 6

- [ ] T105 [US6] Create migration `alembic/versions/005_add_self_service.py` to add dnd_enabled, call_forward_destination, voicemail_pin_hash fields to users table (already in T021, ensure migration exists)
- [ ] T106 [US6] Run migration: `alembic upgrade head` to apply self-service fields
- [ ] T107 [US6] Implement SelfServiceService in `src/services/self_service_service.py` with DND toggle, call forwarding, voicemail PIN change, greeting upload logic
- [ ] T108 [US6] Update internal dialplan generator to check user.dnd_enabled and route to voicemail if DND is ON
- [ ] T109 [US6] Update internal dialplan generator to check user.call_forward_destination and route to forwarded number if set
- [ ] T110 [US6] Add immediate apply for self-service changes: DND/forward changes take effect without full apply operation (write to AstDB or dynamic config)
- [ ] T111 [US6] Create Self-Service API endpoints in `src/api/self_service.py`: GET/PATCH /self-service/me (DND, call forward)
- [ ] T112 [US6] Add voicemail PIN endpoint: PUT /self-service/voicemail/pin with current PIN verification
- [ ] T113 [US6] Add voicemail greeting upload endpoint: POST /self-service/voicemail/greeting with file validation (MP3/WAV, max 5MB)
- [ ] T114 [US6] Implement voicemail greeting file storage: save to Asterisk voicemail directory (/var/spool/asterisk/voicemail/{tenant_id}/{extension}/unavail.wav)
- [ ] T115 [US6] Add audit logging for self-service changes (DND, forward, PIN change, greeting upload)
- [ ] T116 [US6] Restrict self-service endpoints to end_user role using RBAC decorators
- [ ] T117 [US6] Test self-service: End user enables DND → Incoming call goes to voicemail, End user sets forward → Call rings forwarded number, End user changes PIN → New PIN works

**Checkpoint**: User Story 6 complete - End users can manage DND, call forwarding, voicemail without IT support

---

## Phase 9: User Story 7 - Tenant Management for Multi-Tenant Deployments (Priority: P3)

**Goal**: Enable platform admins to manage multiple tenants (companies) on single Asterisk server with complete isolation

**Independent Test**: Create two tenants with overlapping extension ranges → Create users in each → Verify extension 1000 in Tenant A is isolated from extension 1000 in Tenant B → Verify cross-tenant calls are blocked

**Note**: Core multi-tenancy already exists (Tenant model in T020). This phase adds management enhancements.

### Implementation for User Story 7

- [ ] T118 [US7] Create Tenant API endpoints in `src/api/tenants.py`: GET/POST /tenants (platform admin only)
- [ ] T119 [US7] Add Tenant API endpoints: GET/PATCH /tenants/{tenant_id} with extension range updates
- [ ] T120 [US7] Add tenant suspension in TenantService: set tenant.status=suspended, block all calls for suspended tenant
- [ ] T121 [US7] Update internal dialplan generator to check tenant.status and block calls if suspended
- [ ] T122 [US7] Add tenant statistics in Tenants API: GET /tenants/{tenant_id}/stats (total users, total DIDs, extension usage)
- [ ] T123 [US7] Add tenant isolation validation in ApplyValidator: ensure DIDs don't cross tenants, users reference correct tenant
- [ ] T124 [US7] Update RBAC decorators to enforce tenant isolation: tenant_admin can only access own tenant resources
- [ ] T125 [US7] Add platform_admin role enforcement: only platform_admin can create/suspend tenants
- [ ] T126 [US7] Test tenant isolation: Create Tenant A and B with same extension range → Create user 1000 in both → Tenant A user 1000 calls 1002 → Reaches Tenant A's 1002 only

**Checkpoint**: User Story 7 complete - Multi-tenant management with complete isolation and platform admin controls

---

## Phase 10: User Story 8 - Diagnostics and Real-Time Status (Priority: P3)

**Goal**: Enable tenant admins/support users to view real-time device registration status and system health for self-service troubleshooting

**Independent Test**: Register device → View Diagnostics page → Verify shows "Registered" with IP address → Unplug device → Refresh page → Verify shows "Unregistered" within 60 seconds

**Note**: Core diagnostics already implemented (health check in T032, device status in T050). This phase adds enhancements.

### Implementation for User Story 8

- [ ] T127 [US8] Enhance health check endpoint in `src/api/diagnostics.py` to include detailed component status: PostgreSQL, MariaDB, AMI, disk space with latency metrics
- [ ] T128 [US8] Add Asterisk status check in health checker: verify Asterisk process running, AMI responding, dialplan loaded
- [ ] T129 [US8] Add trunk status aggregation endpoint: GET /diagnostics/trunks to show all trunk registration statuses
- [ ] T130 [US8] Add device status aggregation endpoint: GET /diagnostics/devices to show all device registration statuses with filtering by tenant
- [ ] T131 [US8] Implement real-time status updates using AMI events: subscribe to PeerStatus, Registry events for live updates
- [ ] T132 [US8] Add support role read-only access: ensure support users can view diagnostics but cannot modify configs
- [ ] T133 [US8] Add audit log query endpoint in `src/api/audit.py`: GET /audit-logs with filtering by entity_type, action, actor_id, timestamp range
- [ ] T134 [US8] Add pagination to audit log endpoint: support limit/offset or cursor-based pagination
- [ ] T135 [US8] Test diagnostics: Register device → Check /diagnostics/devices shows Registered → Unregister → Check shows Unregistered, Support user logs in → Can view all diagnostics → Cannot apply changes

**Checkpoint**: User Story 8 complete - Diagnostics provide real-time visibility into system health and device status

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, production readiness, and documentation

### Security Hardening

- [ ] T136 [P] Add HTTPS redirect middleware in `src/main.py` (HTTP → HTTPS)
- [ ] T137 [P] Add rate limiting middleware for API endpoints to prevent abuse
- [ ] T138 [P] Add CORS configuration in `src/main.py` with allowed origins from environment variables
- [ ] T139 [P] Ensure all SIP passwords are masked in API responses (return "********" instead of plaintext)
- [ ] T140 [P] Add security headers middleware: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection

### Performance Optimization

- [ ] T141 [P] Add database connection pooling configuration in `src/database.py` and `src/mariadb_connection.py`
- [ ] T142 [P] Add pagination to all list endpoints: Users, Devices, DIDs, Trunks, Policies, Apply Jobs, Audit Logs
- [ ] T143 [P] Add database indexes per data-model.md specifications (tenant_id, status, email, sip_username, did_number, etc.)
- [ ] T144 [P] Implement caching for AMI status queries (30-second TTL) to reduce AMI load

### Error Handling & Logging

- [ ] T145 [P] Add structured error responses with consistent format: {error, message, details}
- [ ] T146 [P] Add request ID tracking for distributed tracing (generate UUID per request, include in logs)
- [ ] T147 [P] Add error logging for all exceptions with stack traces to structured logs
- [ ] T148 [P] Add audit log retention policy documentation (currently indefinite, may need archival strategy)

### Frontend Integration

- [ ] T149 [P] Update frontend `static/js/app.js` to integrate with authentication endpoints (login, refresh, logout)
- [ ] T150 [P] Update frontend to display user list with auto-assigned extensions
- [ ] T151 [P] Update frontend to display device list with registration status
- [ ] T152 [P] Update frontend to display DID assignment UI
- [ ] T153 [P] Update frontend to implement Apply workflow with preview and status tracking
- [ ] T154 [P] Add self-service portal page for end users (DND, call forward, voicemail)
- [ ] T155 [P] Add diagnostics dashboard for admins (device status, trunk status, health check)

### Documentation & Validation

- [ ] T156 [P] Generate OpenAPI JSON schema from FastAPI app: expose at /openapi.json
- [ ] T157 [P] Verify Swagger UI auto-docs at /docs match contracts/openapi.yaml
- [ ] T158 [P] Create database seed script `scripts/seed_db.py` per quickstart.md
- [ ] T159 [P] Create SQL schema script `scripts/sql/pjsip_realtime_schema.sql` for MariaDB tables
- [ ] T160 [P] Update README.md with quickstart instructions and link to quickstart.md
- [ ] T161 Run full quickstart.md validation: verify 15-step setup completes successfully
- [ ] T162 Create systemd service file for production deployment: `pbx-portal.service`

### Final Validation

- [ ] T163 Run end-to-end integration test: Create tenant → Create user → Create device → Assign DID → Apply → Register device → Make test call
- [ ] T164 Verify all 8 user stories are independently testable as documented in spec.md
- [ ] T165 Verify all 28 success criteria from spec.md are measurable and achievable
- [ ] T166 Code review: Check all SIP passwords are encrypted, no secrets in logs, RBAC enforced on all endpoints
- [ ] T167 Security audit: Verify HTTPS only, JWT secrets strong, database passwords not hardcoded
- [ ] T168 Performance test: Verify apply operation completes within 30 seconds for 100 users (SC-009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-10)**: All depend on Foundational phase completion
  - **Phase 3 (US1)**: Can start after Foundational - MVP foundation
  - **Phase 4 (US3)**: Can start after Foundational - Implemented alongside US1 for safe applies
  - **Phase 5 (US2)**: Can start after Foundational - Independent (requires US1 for users to exist, but testable independently)
  - **Phase 6 (US4)**: Extends US1 - Can start after US1 core is complete
  - **Phase 7 (US5)**: Can start after Foundational - Independent (requires US1 for users to make calls)
  - **Phase 8 (US6)**: Extends US1 - Can start after US1 core is complete
  - **Phase 9 (US7)**: Can start after Foundational - Independent (tenant management)
  - **Phase 10 (US8)**: Can start after US1/US2 - Requires devices and DIDs to diagnose
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies (Critical Path)

```
Foundational (Phase 2)
    ↓
US1: User Provisioning (Phase 3) ← MVP CORE
    ↓
US3: Safe Apply (Phase 4) ← MVP CORE (runs alongside US1)
    ↓
┌───┴───┐
│       │
US2     US4 (extends US1)
│       │
US5     US6 (extends US1)
│       │
US7     US8 (extends US1/US2)
│       │
└───┬───┘
    ↓
Polish (Phase 11)
```

**Critical Path for MVP**:
1. Phase 1: Setup
2. Phase 2: Foundational (BLOCKING)
3. Phase 3: US1 (User Provisioning)
4. Phase 4: US3 (Safe Apply)
5. **STOP HERE** for MVP validation before continuing to US2-US8

### Within Each User Story

**General pattern** (adjust based on specific story needs):
1. Models (can run in parallel if no dependencies)
2. Migrations (sequential: create → run upgrade)
3. Services (depend on models)
4. Config Generators (depend on models)
5. API Endpoints (depend on services)
6. Apply Integration (depend on generators)
7. Validation & Audit (depend on services)
8. End-to-end test

### Parallel Opportunities

**Setup (Phase 1)**:
- T003, T004, T005, T006 (dependencies) can run in parallel
- T008, T010 (project structure) can run in parallel

**Foundational (Phase 2)**:
- T016, T017, T018 (auth layer) can run in parallel
- T020, T021, T022, T023 (models) can run in parallel
- T036, T037, T038 (config generators) can run in parallel

**User Story 1 (Phase 3)**:
- T040 (Device model) can run in parallel with T043 (UserService extension)
- T044, T045, T046 (services) can run after models but some parts in parallel

**User Story 2 (Phase 5)**:
- T067 (DID model) can start immediately after Foundational

**User Story 5 (Phase 7)**:
- T088, T089 (Trunk and Policy models) can run in parallel

**Polish (Phase 11)**:
- T136-T140 (security) can run in parallel
- T141-T144 (performance) can run in parallel
- T145-T148 (error handling) can run in parallel
- T149-T155 (frontend) can run in parallel
- T156-T162 (documentation) can run in parallel

---

## Parallel Example: User Story 1 (Phase 3)

```bash
# Step 1: Launch models in parallel (after Foundational complete)
Task T040: Create Device model in src/models/device.py
(in parallel with other foundational work if no conflicts)

# Step 2: Run migration (sequential)
Task T041: Create migration for devices table
Task T042: Run alembic upgrade head

# Step 3: Launch services (after models exist)
Task T043: Extend UserService
Task T044: Implement DeviceService
Task T045: Extend PJSIP Realtime service
(T044 and T045 can run in parallel if working on different files)

# Step 4: Config generators (can run in parallel with services)
Task T046: Update internal dialplan generator

# Step 5: API endpoints (depend on services)
Task T047: Extend User API
Task T048: Create Device API

# Step 6: Integration (sequential, depends on all above)
Task T049: Integrate DeviceService with ApplyService
Task T050: Add device status query
Task T051: Update ApplyService for dialplan
Task T052: Add validations
Task T053: Add audit logging
Task T054: End-to-end test
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 3 Only)

**Minimum Viable Product** - Delivers core value with lowest risk:

1. **Phase 1**: Setup (T001-T010) → ~1 day
2. **Phase 2**: Foundational (T011-T039) → ~3-4 days
3. **Phase 3**: User Story 1 - User Provisioning (T040-T054) → ~3-4 days
4. **Phase 4**: User Story 3 - Safe Apply (T055-T066) → ~2-3 days
5. **STOP and VALIDATE**: Test MVP independently
6. **Deploy/Demo**: Users can create accounts, register phones, make extension calls safely

**MVP Delivers**:
- ✅ User provisioning with auto-extension assignment
- ✅ Multi-device support (desk phone + softphone)
- ✅ Extension-to-extension calling
- ✅ Safe apply workflow with validation and rollback
- ✅ Basic authentication and RBAC
- ✅ Audit trail for all changes

**Total MVP Effort**: ~9-12 days (single developer) or ~5-7 days (2-3 developers in parallel)

---

### Incremental Delivery (Add User Stories Sequentially)

After MVP validation:

**Iteration 2: External Calling** (US2 + US5)
- Add Phase 5: US2 - Inbound DID Routing (T067-T078) → ~2-3 days
- Add Phase 7: US5 - Outbound Calling (T088-T104) → ~3-4 days
- **Value**: Users can now receive external calls and make outbound calls with cost control

**Iteration 3: User Experience** (US4 + US6)
- Add Phase 6: US4 - Multi-Device Enhancements (T079-T087) → ~1-2 days
- Add Phase 8: US6 - Self-Service (T105-T117) → ~2-3 days
- **Value**: Enhanced multi-device management and user autonomy

**Iteration 4: Scalability & Operations** (US7 + US8)
- Add Phase 9: US7 - Tenant Management (T118-T126) → ~2-3 days
- Add Phase 10: US8 - Diagnostics (T127-T135) → ~2-3 days
- **Value**: Multi-tenant SaaS capability and operational visibility

**Iteration 5: Production Readiness**
- Add Phase 11: Polish & Cross-Cutting Concerns (T136-T168) → ~3-5 days
- **Value**: Security hardening, performance optimization, production deployment

**Total Full Implementation**: ~25-35 days (single developer) or ~12-18 days (2-3 developers in parallel)

---

### Parallel Team Strategy

With 3 developers (after Foundational phase complete):

**Week 1-2: MVP Core**
- Developer A: US1 - User Provisioning (Phase 3)
- Developer B: US3 - Safe Apply (Phase 4)
- Developer C: Foundational extensions and testing

**Week 3: External Calling**
- Developer A: US2 - Inbound DID Routing (Phase 5)
- Developer B: US5 - Outbound Calling (Phase 7)
- Developer C: Integration testing

**Week 4: User Experience**
- Developer A: US4 - Multi-Device (Phase 6)
- Developer B: US6 - Self-Service (Phase 8)
- Developer C: Frontend integration

**Week 5: Scalability**
- Developer A: US7 - Tenant Management (Phase 9)
- Developer B: US8 - Diagnostics (Phase 10)
- Developer C: Security hardening

**Week 6: Polish & Launch**
- All developers: Phase 11 - Polish, testing, documentation, deployment

**Total Parallel Effort**: ~6 weeks (3 developers) = ~18 person-days equivalent

---

## Notes

- **[P] tasks** = Different files, no dependencies within phase - can run in parallel
- **[Story] label** = Maps task to specific user story for traceability
- Each user story should be independently completable and testable per spec.md
- **Tests NOT included**: Spec did not explicitly request TDD - tests can be added later if needed
- Commit after each task or logical group of related tasks
- Stop at any checkpoint to validate story independently before proceeding
- **MVP = Phases 1-4** (Setup + Foundational + US1 + US3) - validates core value before investing in remaining stories
- Extension ranges use tenant.ext_next pointer for O(1) allocation (no gaps on delete by design)
- SIP passwords use Fernet encryption (reversible) for MariaDB sync, user passwords use Argon2 (one-way hash)
- PJSIP Realtime violation of Constitution Principle I is justified and documented in plan.md
- Frontend already exists (`static/`) - tasks extend it rather than rewrite
- All Asterisk config writes use atomic temp → move pattern via existing `atomic_writer.py`
- PostgreSQL advisory locks prevent concurrent applies (one apply at a time per tenant)
- Apply workflow: Validate → Lock → Backup → Generate → Write → Reload → Rollback on error

---

## Task Count Summary

- **Phase 1 (Setup)**: 10 tasks
- **Phase 2 (Foundational)**: 29 tasks (T011-T039)
- **Phase 3 (US1 - User Provisioning)**: 15 tasks (T040-T054)
- **Phase 4 (US3 - Safe Apply)**: 12 tasks (T055-T066)
- **Phase 5 (US2 - Inbound DID Routing)**: 12 tasks (T067-T078)
- **Phase 6 (US4 - Multi-Device)**: 9 tasks (T079-T087)
- **Phase 7 (US5 - Outbound Calling)**: 17 tasks (T088-T104)
- **Phase 8 (US6 - Self-Service)**: 13 tasks (T105-T117)
- **Phase 9 (US7 - Tenant Management)**: 9 tasks (T118-T126)
- **Phase 10 (US8 - Diagnostics)**: 9 tasks (T127-T135)
- **Phase 11 (Polish)**: 33 tasks (T136-T168)

**Total Tasks**: 168

**MVP Tasks (Phases 1-4)**: 66 tasks
**Full Feature Tasks (All Phases)**: 168 tasks

**Parallel Opportunities**: ~60 tasks marked [P] can run in parallel within their phases

---

**Ready to implement**: Start with Phase 1 (Setup), then Phase 2 (Foundational), then Phase 3+4 (MVP core)
