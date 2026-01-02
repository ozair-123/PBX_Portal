---

description: "Task list for PBX Control Portal MVP implementation"
---

# Tasks: PBX Control Portal MVP

**Input**: Design documents from `/specs/1-pbx-control-portal/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/api.yaml

**Tests**: Not explicitly requested - tasks focus on implementation only

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below use single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure: src/{models,services,api,config_generator,asterisk}/, tests/{unit,integration,contract}/
- [X] T002 Initialize Python project with pyproject.toml or setup.py
- [X] T003 [P] Create requirements.txt with dependencies: fastapi, uvicorn[standard], sqlalchemy[asyncio], psycopg2-binary, alembic, python-dotenv, pydantic[email], pytest, pytest-asyncio
- [X] T004 [P] Create .env.example template with DATABASE_URL and LOG_LEVEL placeholders
- [X] T005 [P] Create .gitignore for Python (.env, __pycache__/, *.pyc, venv/, .pytest_cache/)
- [X] T006 [P] Create README.md with quickstart setup instructions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Initialize Alembic migrations in migrations/ directory
- [X] T008 Configure Alembic env.py with database connection from environment variable DATABASE_URL
- [X] T009 [P] Create database models: Tenant model in src/models/tenant.py (id:UUID, name:str, created_at:datetime)
- [X] T010 [P] Create database models: User model in src/models/user.py (id:UUID, tenant_id:UUID FK, name:str, email:str unique, created_at:datetime)
- [X] T011 [P] Create database models: Extension model in src/models/extension.py (id:UUID, number:int unique 1000-1999, user_id:UUID unique FK, secret:str, created_at:datetime)
- [X] T012 [P] Create database models: ApplyAuditLog model in src/models/apply_audit_log.py (id:UUID, triggered_at:datetime, triggered_by:str, outcome:str enum, error_details:text, files_written:array, reload_results:jsonb)
- [X] T013 Create Alembic migration 001_initial_schema.py for all models (tenants, users, extensions, apply_audit_logs tables)
- [X] T014 Create Alembic data migration 002_default_tenant.py to insert default tenant with id='a0000000-0000-0000-0000-000000000000', name='Default'
- [X] T015 Create database session manager in src/database.py (async SQLAlchemy session with connection pooling)
- [X] T016 Create environment config loader in src/config.py (load DATABASE_URL, LOG_LEVEL from .env using python-dotenv)
- [X] T017 Create FastAPI application instance in src/main.py with basic setup (CORS if needed, exception handlers, lifespan events)
- [X] T018 Configure Python logging in src/logging_config.py (structured logging, log level from config)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create User with Extension Allocation (Priority: P1) 🎯 MVP

**Goal**: Enable admins to create users with auto-allocated SIP extensions (1000-1999)

**Independent Test**: Create user via POST /users, verify extension allocated in range 1000-1999, stored in database

### Implementation for User Story 1

- [X] T019 [P] [US1] Create ExtensionAllocator service in src/services/extension_allocator.py with allocate_extension(session, user_id, max_retries=5) using MIN query with concurrency-safe retry logic
- [X] T020 [P] [US1] Create SIP secret generator function in src/services/extension_allocator.py using secrets.token_urlsafe(16)
- [X] T021 [US1] Create UserService in src/services/user_service.py with create_user(name, email) method that: validates input, starts transaction, creates User, calls ExtensionAllocator, commits, returns User+Extension
- [X] T022 [US1] Implement POST /users endpoint in src/api/users.py using FastAPI router, call UserService.create_user(), return 201 with user+extension JSON, handle validation errors (400), pool exhausted (409), server errors (500)
- [X] T023 [US1] Add input validation with Pydantic models in src/api/schemas.py: CreateUserRequest (name, email), UserResponse (id, tenant_id, name, email, extension:{number, secret}, created_at)
- [X] T024 [US1] Register users router in src/main.py with app.include_router(users_router, prefix="/users", tags=["users"])

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (create users via API, extensions allocated)

---

## Phase 4: User Story 2 - Apply Configuration to Asterisk (Priority: P1) 🎯 MVP

**Goal**: Apply database changes to live Asterisk server by generating configs and reloading modules

**Independent Test**: Create users in DB (US1), call POST /apply, verify generated config files exist at /etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf and /etc/asterisk/extensions.d/synergycall/generated_routing.conf with correct syntax

### Implementation for User Story 2

- [X] T025 [P] [US2] Create PJSIPGenerator in src/config_generator/pjsip_generator.py with generate_config(users_with_extensions) returning string with endpoint+auth+aor blocks per extension
- [X] T026 [P] [US2] Create DialplanGenerator in src/config_generator/dialplan_generator.py with generate_config(users_with_extensions) returning string with [synergy-internal] context and exten => lines
- [X] T027 [P] [US2] Create AtomicFileWriter in src/config_generator/atomic_writer.py with write_atomic(content, target_path) using tempfile.NamedTemporaryFile + os.replace pattern
- [X] T028 [P] [US2] Create AsteriskReloader in src/asterisk/reloader.py with reload_pjsip() and reload_dialplan() using subprocess.run(["asterisk", "-rx", "..."]), capture exit codes, stdout, stderr
- [X] T029 [US2] Create ApplyService in src/services/apply_service.py with apply_configuration(triggered_by) method that: acquires PostgreSQL advisory lock (pg_advisory_lock), reads all users/extensions, calls generators, calls AtomicFileWriter for both files, calls AsteriskReloader, creates ApplyAuditLog, releases lock
- [X] T030 [US2] Implement POST /apply endpoint in src/api/apply.py using FastAPI router, call ApplyService.apply_configuration(), return 200 with audit_log_id + files_written + reload_results, handle lock conflict (409), apply failures (500)
- [X] T031 [US2] Add Pydantic models in src/api/schemas.py: ApplyRequest (triggered_by), ApplyResponse (message, audit_log_id, files_written, reload_results, users_applied, extensions_generated), ApplyErrorResponse
- [X] T032 [US2] Register apply router in src/main.py with app.include_router(apply_router, prefix="/apply", tags=["apply"])

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (create users + apply config → Asterisk has endpoints)

---

## Phase 5: User Story 3 - List Users (Priority: P2)

**Goal**: Retrieve all users and their assigned extensions for operational visibility

**Independent Test**: Create several users (US1), call GET /users, verify all users returned with correct extensions

### Implementation for User Story 3

- [ ] T033 [US3] Add list_all_users() method to UserService in src/services/user_service.py that queries all users with joined extensions, returns list
- [ ] T034 [US3] Implement GET /users endpoint in src/api/users.py, call UserService.list_all_users(), return 200 with users array, handle database errors (500)
- [ ] T035 [US3] Add Pydantic model in src/api/schemas.py: ListUsersResponse (users: array of UserResponse)

**Checkpoint**: All user stories 1-3 should now be independently functional (create, apply, list)

---

## Phase 6: User Story 4 - Delete User (Priority: P3)

**Goal**: Remove users and free their extensions for reuse

**Independent Test**: Create user (US1), delete via DELETE /users/{id}, verify removal from DB and extension freed for reuse

### Implementation for User Story 4

- [ ] T036 [US4] Add delete_user(user_id) method to UserService in src/services/user_service.py that deletes User (cascade deletes Extension), returns deleted extension number
- [ ] T037 [US4] Implement DELETE /users/{userId} endpoint in src/api/users.py, call UserService.delete_user(), return 200 with message + freed_extension, handle not found (404), database errors (500)
- [ ] T038 [US4] Add Pydantic model in src/api/schemas.py: DeleteUserResponse (message, deleted_user_id, freed_extension)

**Checkpoint**: All user stories should now be independently functional (create, apply, list, delete)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T039 [P] Add comprehensive error handling middleware in src/main.py for uncaught exceptions (return 500 with generic message, log detailed error)
- [ ] T040 [P] Add request logging middleware in src/main.py (log request method, path, status code, duration)
- [ ] T041 [P] Create health check endpoint GET /health in src/api/health.py that verifies database connection, returns 200 with status
- [ ] T042 [P] Update README.md with complete setup instructions, environment variables, running migrations, starting server
- [ ] T043 [P] Add docstrings to all service classes and public methods
- [ ] T044 Add validation for extension pool exhaustion error message clarity in UserService
- [ ] T045 Add retry limit exhaustion error message in ExtensionAllocator
- [ ] T046 Verify all API responses match OpenAPI spec in contracts/api.yaml

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P1): Can start after Foundational - Functionally depends on US1 (needs users to apply), but can be developed in parallel with mocked data
  - User Story 3 (P2): Can start after Foundational - No hard dependencies on US1/US2, but needs US1 for meaningful testing
  - User Story 4 (P3): Can start after Foundational - No hard dependencies, but needs US1 for meaningful testing
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Development can proceed in parallel with US1 (use mocked user data for testing config generation)
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independently testable but more meaningful with US1 users
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Independently testable but more meaningful with US1 users

### Within Each User Story

User Story 1 (Create User):
- T019, T020 (ExtensionAllocator + secret generator) have no dependencies - can run in parallel
- T021 (UserService) depends on T019, T020
- T022, T023 (API endpoint + schemas) depend on T021
- T024 (router registration) depends on T022, T023

User Story 2 (Apply):
- T025, T026, T027, T028 (generators + atomic writer + reloader) have no dependencies - can run in parallel
- T029 (ApplyService) depends on T025, T026, T027, T028
- T030, T031 (API endpoint + schemas) depend on T029
- T032 (router registration) depends on T030, T031

User Story 3 (List Users):
- T033 (UserService.list_all_users) has no dependencies (extends existing UserService)
- T034, T035 (API endpoint + schemas) depend on T033

User Story 4 (Delete User):
- T036 (UserService.delete_user) has no dependencies (extends existing UserService)
- T037, T038 (API endpoint + schemas) depend on T036

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004, T005, T006)
- All Foundational model tasks can run in parallel (T009, T010, T011, T012)
- Once Foundational phase completes, User Stories 1-4 can be developed in parallel by different developers
- Within User Story 1: T019 and T020 can run in parallel
- Within User Story 2: T025, T026, T027, T028 can run in parallel
- All Polish tasks marked [P] can run in parallel (T039, T040, T041, T042, T043)

---

## Parallel Example: User Story 1

```bash
# Launch extension allocator and secret generator in parallel:
Task T019: "Create ExtensionAllocator service in src/services/extension_allocator.py"
Task T020: "Create SIP secret generator in src/services/extension_allocator.py"

# After both complete, create UserService:
Task T021: "Create UserService in src/services/user_service.py"

# After UserService, create API endpoint and schemas in parallel:
Task T022: "Implement POST /users endpoint in src/api/users.py"
Task T023: "Add input validation with Pydantic models in src/api/schemas.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch all config generators in parallel:
Task T025: "Create PJSIPGenerator in src/config_generator/pjsip_generator.py"
Task T026: "Create DialplanGenerator in src/config_generator/dialplan_generator.py"
Task T027: "Create AtomicFileWriter in src/config_generator/atomic_writer.py"
Task T028: "Create AsteriskReloader in src/asterisk/reloader.py"

# After all complete, create ApplyService:
Task T029: "Create ApplyService in src/services/apply_service.py"

# After ApplyService, create API endpoint and schemas in parallel:
Task T030: "Implement POST /apply endpoint in src/api/apply.py"
Task T031: "Add Pydantic models in src/api/schemas.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T018) - CRITICAL foundation
3. Complete Phase 3: User Story 1 (T019-T024)
4. **STOP and VALIDATE**: Test user creation independently via curl or Swagger UI
5. Complete Phase 4: User Story 2 (T025-T032)
6. **STOP and VALIDATE**: Test full flow (create user → apply config → verify Asterisk configs)
7. Deploy/demo if ready

**MVP delivers**: Create users with auto-allocated extensions + apply to Asterisk = working PBX provisioning system

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (user creation working)
3. Add User Story 2 → Test independently → Deploy/Demo (MVP complete! Users can call)
4. Add User Story 3 → Test independently → Deploy/Demo (operational visibility)
5. Add User Story 4 → Test independently → Deploy/Demo (full CRUD)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T018)
2. Once Foundational is done:
   - Developer A: User Story 1 (T019-T024)
   - Developer B: User Story 2 (T025-T032)
   - Developer C: User Story 3 (T033-T035)
   - Developer D: User Story 4 (T036-T038)
3. Stories complete and integrate independently
4. Team completes Polish together (T039-T046)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **No tests included** - tests not explicitly requested in spec (implementation focus only)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Count Summary

- **Phase 1 (Setup)**: 6 tasks
- **Phase 2 (Foundational)**: 12 tasks
- **Phase 3 (User Story 1 - P1)**: 6 tasks
- **Phase 4 (User Story 2 - P1)**: 8 tasks
- **Phase 5 (User Story 3 - P2)**: 3 tasks
- **Phase 6 (User Story 4 - P3)**: 3 tasks
- **Phase 7 (Polish)**: 8 tasks

**Total**: 46 tasks

**MVP Scope** (User Story 1 + 2): 26 tasks (Setup + Foundational + US1 + US2)

**Parallel Opportunities**: 15 tasks marked [P] can run in parallel when dependencies are met
