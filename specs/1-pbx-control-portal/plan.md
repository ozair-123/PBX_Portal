# Implementation Plan: PBX Control Portal MVP

**Branch**: `1-pbx-control-portal` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/1-pbx-control-portal/spec.md`

## Summary

Backend-only PBX control portal for Asterisk 22.7.0 that enables administrators to create users with auto-allocated SIP extensions (1000-1999), store data in PostgreSQL, and apply configuration to Asterisk via generated include files. Core MVP loop: create user → apply config → user can register and call.

Technical approach: REST API service runs on Asterisk server (65.108.92.238), connects to PostgreSQL (user/extension data). Apply action generates PJSIP endpoint+auth+aor config and dialplan routing, writes atomically to include directories, reloads Asterisk modules via local subprocess, logs audit trail.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI (REST API), SQLAlchemy (ORM), Psycopg2 (PostgreSQL driver), subprocess (local Asterisk commands)
**Storage**: PostgreSQL at 77.42.28.222 (Tenant, User, Extension, ApplyAuditLog tables)
**Testing**: pytest with pytest-asyncio for async tests
**Target Platform**: Linux server at 65.108.92.238 (co-located with Asterisk), connects to Postgres at 77.42.28.222
**Project Type**: Single backend service (no frontend in MVP)
**Performance Goals**: <2s user creation, <10s apply for 100 users, <1s list 500 users
**Constraints**: Asterisk 22.7.0 PJSIP-only, extension range 1000-1999 (1000 max), atomic file writes, explicit apply only
**Scale/Scope**: Single tenant, 1000 max extensions, MVP backend API only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. File-Based Asterisk Configuration ✅
- **Requirement**: Asterisk MUST remain file-based (no Realtime)
- **Compliance**: Design uses generated include files only (PJSIP/dialplan .conf files)
- **Status**: PASS

### II. Isolated Configuration Generation ✅
- **Requirement**: Portal MUST only write include files, not core Asterisk files
- **Compliance**: Writes to /etc/asterisk/pjsip.d/synergycall/ and /etc/asterisk/extensions.d/synergycall/ only
- **Status**: PASS

### III. Atomic File Operations ✅
- **Requirement**: Config writes MUST be atomic (write temp → move)
- **Compliance**: Apply action explicitly uses temp file → rename pattern
- **Status**: PASS

### IV. Explicit Apply Actions ✅
- **Requirement**: Asterisk reloads only via explicit user action
- **Compliance**: POST /apply endpoint required - no automatic reloads
- **Status**: PASS

### V. Strict Scope Adherence ✅
- **Requirement**: No features outside specification
- **Compliance**: Spec defines exactly 4 APIs (create user, apply, list, delete) - no extras
- **Status**: PASS

### VI. No Frontend in MVP ✅
- **Requirement**: No UI unless specified
- **Compliance**: Backend API only per spec
- **Status**: PASS

### VII. No Hardcoded Secrets ✅
- **Requirement**: Use environment variables for secrets
- **Compliance**: Database credentials, Asterisk SSH credentials in .env
- **Status**: PASS

### VIII. Simplicity First ✅
- **Requirement**: Simplest implementation meeting requirements
- **Compliance**: FastAPI (minimal web framework), SQLAlchemy (standard ORM), no complex abstractions
- **Status**: PASS

**Overall Constitution Compliance**: ✅ PASS - All 8 principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/1-pbx-control-portal/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (technology decisions)
├── data-model.md        # Phase 1 output (database schema)
├── quickstart.md        # Phase 1 output (setup instructions)
├── contracts/           # Phase 1 output (API contracts)
│   └── api.yaml         # OpenAPI 3.0 spec
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── models/              # SQLAlchemy models (Tenant, User, Extension, ApplyAuditLog)
├── services/            # Business logic (UserService, ApplyService, ExtensionAllocator)
├── api/                 # FastAPI routers (users.py, apply.py)
├── config_generator/    # Asterisk config generators (PJSIPGenerator, DialplanGenerator)
├── asterisk/            # Local Asterisk command executor (AsteriskReloader)
└── main.py              # FastAPI application entry point

tests/
├── contract/            # API contract tests (OpenAPI compliance)
├── integration/         # End-to-end tests (DB + config generation + mocked subprocess)
└── unit/                # Unit tests for services and generators

.env.example             # Template for environment variables
requirements.txt         # Python dependencies
README.md                # Project setup and running instructions
```

**Structure Decision**: Single project structure selected. Backend-only service with clear separation: models (data), services (business logic), api (HTTP layer), config_generator (Asterisk file generation), asterisk (local command execution). No frontend directory needed (MVP is API-only per constitution principle VI). Portal runs co-located with Asterisk server for simplicity (no remote SSH needed).

## Complexity Tracking

No constitution violations requiring justification.

## Phase 0: Research (Technology Decisions)

**Status**: COMPLETE (see research.md)
**Artifacts**: [research.md](research.md)

Key decisions:
- Python 3.11 + FastAPI for REST API (lightweight, async support, auto OpenAPI docs)
- SQLAlchemy + Psycopg2 for PostgreSQL (standard Python ORM)
- subprocess for local Asterisk commands (portal co-located with Asterisk)
- pytest for testing (industry standard)
- Atomic file writes via tempfile.NamedTemporaryFile + os.replace
- Concurrency-safe extension allocation (DB transaction + unique constraint + retry logic)

See research.md for full rationale and alternatives considered.

## Phase 1: Design Artifacts

**Status**: COMPLETE
**Artifacts**: [data-model.md](data-model.md), [contracts/api.yaml](contracts/api.yaml), [quickstart.md](quickstart.md)

### Data Model Summary

4 entities: Tenant (single default), User (name, email), Extension (number 1000-1999), ApplyAuditLog (timestamp, outcome, details)

Key relationships:
- User → Extension (one-to-one)
- User → Tenant (many-to-one)
- Extension allocation algorithm: SELECT MIN(num) WHERE num NOT IN (allocated) AND num BETWEEN 1000 AND 1999
- Concurrency safety: UNIQUE constraint on extension.number + DB transaction + retry on conflict

See data-model.md for complete schema.

### API Contracts Summary

4 REST endpoints:
- POST /users - Create user, allocate extension
- GET /users - List all users with extensions
- DELETE /users/{id} - Delete user, free extension
- POST /apply - Generate Asterisk config, write atomically, reload

See contracts/api.yaml for full OpenAPI specification.

### Quickstart Summary

Setup steps:
1. Clone repo, install Python 3.11
2. Install dependencies: pip install -r requirements.txt
3. Configure .env (DB credentials, Asterisk SSH details)
4. Run migrations: alembic upgrade head
5. Start server: uvicorn src.main:app
6. Test: curl http://localhost:8000/docs (Swagger UI)

See quickstart.md for detailed instructions.

## Phase 2: Task Breakdown

**Status**: NOT STARTED
**Command**: Run `/sp.tasks` to generate tasks.md

Tasks will be organized by user story (P1: Create User, P1: Apply Config, P2: List Users, P3: Delete User) with test-first approach if requested.

---

## Post-Design Constitution Re-Check

*Re-evaluating all 8 principles after completing design artifacts*

### I. File-Based Asterisk Configuration ✅
- **Design Compliance**: PJSIPGenerator and DialplanGenerator produce .conf files only
- **Evidence**: contracts/api.yaml POST /apply generates files at /etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf and /etc/asterisk/extensions.d/synergycall/generated_routing.conf
- **Status**: PASS

### II. Isolated Configuration Generation ✅
- **Design Compliance**: Config generators write only to designated include directories
- **Evidence**: data-model.md shows no tables for core Asterisk config; quickstart.md requires manual include directives as prerequisite
- **Status**: PASS

### III. Atomic File Operations ✅
- **Design Compliance**: Apply service uses tempfile + os.replace pattern
- **Evidence**: research.md documents atomic write strategy with Python tempfile.NamedTemporaryFile
- **Status**: PASS

### IV. Explicit Apply Actions ✅
- **Design Compliance**: User/extension CRUD operations do not trigger Asterisk changes
- **Evidence**: contracts/api.yaml separates POST /users (DB only) from POST /apply (Asterisk reload)
- **Status**: PASS

### V. Strict Scope Adherence ✅
- **Design Compliance**: Exactly 4 endpoints match spec requirements, no additional features
- **Evidence**: contracts/api.yaml defines only POST /users, GET /users, DELETE /users/{id}, POST /apply
- **Status**: PASS

### VI. No Frontend in MVP ✅
- **Design Compliance**: Project structure has no frontend/ directory, only src/ backend
- **Evidence**: plan.md project structure shows single backend service only
- **Status**: PASS

### VII. No Hardcoded Secrets ✅
- **Design Compliance**: All credentials loaded from environment variables
- **Evidence**: quickstart.md requires .env configuration; .env.example provides template
- **Status**: PASS

### VIII. Simplicity First ✅
- **Design Compliance**: Minimal dependencies (FastAPI, SQLAlchemy, subprocess stdlib), no complex frameworks
- **Evidence**: research.md selects lightweight tools; portal co-located with Asterisk (no SSH complexity); no DDD layers, no microservices, no event bus
- **Status**: PASS

**Final Constitution Compliance**: ✅ PASS - All 8 principles satisfied in design

---

## Design Complete - Ready for Tasks

Branch: `1-pbx-control-portal`
Plan: `specs/1-pbx-control-portal/plan.md`
Artifacts:
- [research.md](research.md) - Technology decisions and rationale
- [data-model.md](data-model.md) - Database schema and relationships
- [contracts/api.yaml](contracts/api.yaml) - OpenAPI 3.0 specification
- [quickstart.md](quickstart.md) - Setup and run instructions

**Next Step**: Run `/sp.tasks` to generate actionable task breakdown organized by user story.
