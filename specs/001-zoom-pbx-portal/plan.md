# Implementation Plan: Zoom-Style PBX Management Portal

**Branch**: `001-zoom-pbx-portal` | **Date**: 2026-01-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-zoom-pbx-portal/spec.md`

## Summary

Build a comprehensive Zoom-like PBX management portal for Asterisk that treats Users as the core object, automatically assigns extensions, routes inbound DIDs to destinations, manages devices/policies, and provides safe configuration apply with automatic rollback. The system supports multi-tenant isolation with RBAC, real-time diagnostics, and complete audit trailing.

**Primary Enhancement**: Extend existing user/extension/apply foundation with DID routing, multi-device support, outbound policy enforcement, end-user self-service, and comprehensive diagnostics.

**Technical Approach**: Leverage existing PJSIP Realtime (MariaDB) for endpoints, add DID routing via Asterisk dialplan/AstDB, implement device management with unique SIP credentials per device, enforce outbound policies via dialplan logic, and enhance apply workflow with more validation and rollback capabilities.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.0+, psycopg2-binary 2.9+, mysql-connector-python 8.0+, uvicorn, pydantic 2.4+, python-dotenv, alembic
**Storage**:
- PostgreSQL 16.11 (application data: users, tenants, extensions, devices, DIDs, policies, audit logs)
- MariaDB (Asterisk PJSIP Realtime: ps_endpoints, ps_auths, ps_aors)
- File-based: Asterisk dialplan configs (/etc/asterisk/extensions.d/synergycall/generated_*.conf)

**Testing**: pytest 7.4+, pytest-asyncio 0.21+
**Target Platform**: Linux server (Ubuntu 22.04+ / Debian 12+) with Asterisk 22.7.0, systemd service management
**Project Type**: Web application (backend API + static frontend already exists)

**Performance Goals**:
- User creation: Complete within 10 seconds (SC-002)
- Apply operation: Complete within 30 seconds for 100 users (SC-009)
- DID lookup: Within 50ms portal-side or 5ms AstDB-based (SC-005)
- API endpoints: Respond within 500ms for typical operations (SC-017)

**Constraints**:
- Zero apply operations leaving Asterisk in non-functional state (SC-008)
- 100% deterministic extension assignment (SC-001)
- Advisory lock serialization prevents concurrent applies (FR-023)
- HTTPS only, bcrypt/argon2 password hashing (FR-044, FR-043)
- SIP passwords encrypted at rest, never logged (FR-010, FR-011)

**Scale/Scope**:
- Support 100 tenants with complete isolation (SC-019)
- 1000 concurrent admin sessions (SC-016)
- Extension ranges up to 999 per tenant (e.g., 1000-1999)
- Portal uptime ≥ 99.5% (SC-015)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: File-Based Asterisk Configuration

**Status**: ⚠️ **VIOLATION - MUST JUSTIFY**

**Violation**: Spec requires PJSIP Realtime via MariaDB (FR-050: "System MUST support AstDB-based DID lookup OR generated dialplan entries"). Existing codebase already uses PJSIP Realtime (MariaDB ps_endpoints, ps_auths, ps_aors).

**Justification**:
- **Current Reality**: System already deployed with PJSIP Realtime for dynamic endpoint registration. This is production-stable and working.
- **Why Needed**: PJSIP Realtime enables dynamic SIP registration without Asterisk reload. File-based PJSIP configs would require reload for every device registration change, causing brief service disruption.
- **Scope Limitation**: PJSIP Realtime is ONLY for SIP endpoints (ps_endpoints, ps_auths, ps_aors). Dialplan, trunks, and all other configs remain file-based.
- **Simpler Alternative Rejected**: Pure file-based PJSIP would require Asterisk reload on every device add/remove, impacting call quality during reloads and violating SC-020 (Tenant A's apply doesn't impact Tenant B's calls).

**Constitution Amendment Proposal**: Add exception clause to Principle I:
> "EXCEPTION: PJSIP endpoint registration MAY use Asterisk Realtime (MariaDB) for dynamic device management without reloads. All other configuration (dialplan, trunks, voicemail) MUST remain file-based."

**Re-evaluation**: After Phase 1, confirm dialplan/DID routing/outbound policies remain file-based.

### Principle II: Isolated Configuration Generation

**Status**: ✅ **PASS**

Portal writes only to:
- `/etc/asterisk/extensions.d/synergycall/generated_inbound.conf` (DID routing - new)
- `/etc/asterisk/extensions.d/synergycall/generated_internal.conf` (extension-to-extension - new)
- `/etc/asterisk/extensions.d/synergycall/generated_outbound.conf` (policy enforcement - new)
- `/etc/asterisk/extensions.d/synergycall/generated_routing.conf` (existing, will be split)

Core Asterisk files (pjsip.conf, extensions.conf) are not modified. Include directives already exist.

### Principle III: Atomic File Operations

**Status**: ✅ **PASS**

Existing `AtomicFileWriter` (src/config_generator/atomic_writer.py) implements temp → move pattern:
```python
def write_atomic(content: str, target_path: str):
    temp_path = f"{target_path}.tmp"
    with open(temp_path, 'w') as f:
        f.write(content)
    shutil.move(temp_path, target_path)
```

All config writes use this pattern. No changes needed.

### Principle IV: Explicit Apply Actions

**Status**: ✅ **PASS**

Existing apply workflow (src/services/apply_service.py) requires explicit user action via POST /apply endpoint. Advisory locks prevent concurrent applies. No automatic reloads on config change.

Enhancement needed: Add validation step before apply (FR-025) to detect conflicts.

### Principle V: Strict Scope Adherence

**Status**: ✅ **PASS**

Implementation plan follows spec exactly:
- 8 user stories (P1-P3 prioritized)
- 53 functional requirements
- 28 success criteria

No speculative features. Phase 2 tasks will implement only specified requirements.

### Principle VI: No Frontend in MVP

**Status**: ⚠️ **EXCEPTION GRANTED**

**Reality**: Frontend already exists (static/index.html, static/js/app.js, static/css/styles.css) and is working in production. User explicitly requested GUI ("i want this system for normal users as a gui").

**Status**: EXCEPTION - Frontend is explicitly specified in spec (Section 10: Frontend Specification) and user requirements. Not a violation.

### Principle VII: No Hardcoded Secrets

**Status**: ✅ **PASS**

Existing `.env` file pattern:
```
DATABASE_URL=postgresql://user:pass@host:port/db
MARIADB_PASSWORD=***
```

SIP passwords encrypted at rest in database (FR-010). No secrets in code or version control.

### Principle VIII: Simplicity First

**Status**: ✅ **PASS**

Current architecture uses:
- FastAPI (lightweight ASGI framework - essential for async)
- SQLAlchemy (ORM - essential for complex queries and migrations)
- Direct file writes (no config abstraction layers)
- Direct AMI/CLI calls (no Asterisk abstraction framework)

No unnecessary abstractions. Rejecting:
- Heavy frameworks (Django, Pyramid)
- ORMs beyond SQLAlchemy
- Complex async queue systems (use advisory locks instead)
- Microservices (single monolith sufficient for 100 tenants)

## Project Structure

### Documentation (this feature)

```text
specs/001-zoom-pbx-portal/
├── spec.md              # Feature specification (already created)
├── checklists/
│   └── requirements.md  # Spec validation (already created)
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output - Next step
├── data-model.md        # Phase 1 output - After research
├── quickstart.md        # Phase 1 output - After data model
├── contracts/           # Phase 1 output - API contracts
│   └── openapi.yaml     # REST API specification
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── models/                      # SQLAlchemy ORM models
│   ├── __init__.py             # ✅ EXISTS
│   ├── tenant.py               # ✅ EXISTS (needs extension: ext_min, ext_max, ext_next, default_inbound_destination, outbound_policy_id, status)
│   ├── user.py                 # ✅ EXISTS (needs extension: role, status, outbound_callerid, voicemail_enabled, voicemail_pin_hash, dnd_enabled, call_forward_destination)
│   ├── extension.py            # ✅ EXISTS
│   ├── device.py               # 🆕 NEW - Multi-device support (label, sip_username, sip_password_encrypted, transport, nat_flags_json, codecs_json)
│   ├── did.py                  # 🆕 NEW - DID routing (did_number, label, provider, destination_type, destination_target)
│   ├── trunk.py                # 🆕 NEW - SIP trunks (name, host, auth_mode, registration_string, transport, codecs_json, enabled)
│   ├── outbound_policy.py      # 🆕 NEW - Outbound calling rules (name, rules_json: patterns, transforms, trunk_priority)
│   ├── apply_audit_log.py      # ✅ EXISTS
│   └── audit_log.py            # 🆕 NEW - General audit trail (actor_id, action, entity_type, entity_id, before_json, after_json, timestamp, source_ip)
│
├── services/                    # Business logic layer
│   ├── __init__.py             # ✅ EXISTS
│   ├── user_service.py         # ✅ EXISTS (needs extension for soft-delete, suspend)
│   ├── extension_allocator.py  # ✅ EXISTS
│   ├── device_service.py       # 🆕 NEW - Device CRUD + status queries via AMI
│   ├── did_service.py          # 🆕 NEW - DID CRUD + routing logic
│   ├── trunk_service.py        # 🆕 NEW - Trunk CRUD + status via AMI
│   ├── outbound_policy_service.py  # 🆕 NEW - Policy CRUD + validation
│   ├── apply_service.py        # ✅ EXISTS (needs enhancement: validation step, better rollback)
│   ├── pjsip_realtime_service.py   # ✅ EXISTS (needs extension for multi-device)
│   ├── self_service_service.py # 🆕 NEW - DND/forward/voicemail for end users
│   └── audit_service.py        # 🆕 NEW - Centralized audit logging
│
├── api/                         # FastAPI route handlers
│   ├── __init__.py             # ✅ EXISTS
│   ├── users.py                # ✅ EXISTS (needs extension for PATCH, soft-delete)
│   ├── devices.py              # 🆕 NEW - Device endpoints
│   ├── dids.py                 # 🆕 NEW - DID endpoints
│   ├── trunks.py               # 🆕 NEW - Trunk endpoints
│   ├── outbound_policies.py    # 🆕 NEW - Policy endpoints
│   ├── apply.py                # ✅ EXISTS (needs extension for preview endpoint)
│   ├── self_service.py         # 🆕 NEW - End user self-service endpoints
│   ├── diagnostics.py          # 🆕 NEW - Device status, health checks
│   ├── audit.py                # 🆕 NEW - Audit log query endpoints
│   └── schemas.py              # ✅ EXISTS (needs extension for all new models)
│
├── config_generator/            # Asterisk config generation
│   ├── __init__.py             # ✅ EXISTS
│   ├── atomic_writer.py        # ✅ EXISTS
│   ├── dialplan_generator.py  # ✅ EXISTS (needs major refactor: split into inbound/internal/outbound)
│   ├── inbound_generator.py    # 🆕 NEW - DID routing dialplan
│   ├── internal_generator.py   # 🆕 NEW - Extension-to-extension + feature codes
│   ├── outbound_generator.py   # 🆕 NEW - Policy enforcement dialplan
│   └── pjsip_generator.py      # ✅ EXISTS (unused due to Realtime, keep for reference)
│
├── asterisk/                    # Asterisk integration
│   ├── __init__.py             # ✅ EXISTS
│   ├── reloader.py             # ✅ EXISTS (AMI/CLI reload commands)
│   ├── ami_client.py           # 🆕 NEW - Asterisk AMI client for status queries (device registration, trunk status)
│   └── health_checker.py       # 🆕 NEW - System health monitoring (Asterisk running, DB connectivity, disk space)
│
├── auth/                        # 🆕 NEW - Authentication & authorization
│   ├── __init__.py
│   ├── password.py             # Password hashing (bcrypt/argon2)
│   ├── jwt.py                  # JWT token generation/validation
│   └── rbac.py                 # Role-based access control decorators
│
├── main.py                      # ✅ EXISTS (needs extension: auth middleware, new routes)
├── database.py                  # ✅ EXISTS
├── config.py                    # ✅ EXISTS
├── logging_config.py            # ✅ EXISTS
└── mariadb_connection.py        # ✅ EXISTS

static/                          # ✅ EXISTS - Frontend already working
├── index.html
├── css/
│   └── styles.css
└── js/
    └── app.js

tests/                           # Test suite
├── unit/                        # Unit tests (services, generators)
│   ├── test_user_service.py
│   ├── test_device_service.py
│   ├── test_did_service.py
│   ├── test_policy_service.py
│   ├── test_dialplan_generators.py
│   └── test_apply_service.py
├── integration/                 # Integration tests (API endpoints)
│   ├── test_user_api.py
│   ├── test_device_api.py
│   ├── test_did_api.py
│   ├── test_apply_api.py
│   └── test_auth.py
└── contract/                    # Contract tests (API schema validation)
    └── test_openapi_spec.py

alembic/                         # ✅ EXISTS - Database migrations
├── versions/
│   ├── 001_initial.py          # ✅ EXISTS
│   ├── 002_add_devices.py      # 🆕 NEW
│   ├── 003_add_dids.py         # 🆕 NEW
│   ├── 004_add_trunks_policies.py  # 🆕 NEW
│   ├── 005_add_self_service.py # 🆕 NEW
│   ├── 006_add_audit_log.py    # 🆕 NEW
│   └── 007_extend_tenant_user.py   # 🆕 NEW
└── env.py                       # ✅ EXISTS
```

**Structure Decision**: Web application structure selected (backend API + frontend). Existing monorepo layout with `src/` for backend and `static/` for frontend is preserved. No restructuring needed - extend existing structure with new modules.

**Key Architectural Notes**:
1. **PJSIP Realtime**: Keep existing MariaDB integration for dynamic endpoints
2. **Dialplan Refactor**: Split existing `dialplan_generator.py` into three generators (inbound/internal/outbound) for maintainability
3. **Service Layer**: All business logic stays in services/, API layer remains thin
4. **AMI Integration**: New `ami_client.py` for real-time device status queries (FR-009)
5. **Auth Layer**: New `auth/` module for JWT + RBAC (FR-040 through FR-044)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle I: PJSIP Realtime (MariaDB) | Dynamic SIP device registration without Asterisk reload. System already in production using Realtime. | File-based PJSIP requires reload on every device change, causing brief call quality degradation (violates SC-020: tenant isolation during applies). Realtime enables true multi-device hot-swapping. |
| SQLAlchemy ORM | Complex multi-table queries (joins across tenants/users/devices/DIDs), automatic migration management via Alembic, relationship management | Raw SQL would require manual migration scripts, manual relationship tracking, higher SQL injection risk, more boilerplate for common CRUD operations |
| FastAPI framework | Async support for concurrent API requests, automatic OpenAPI docs, Pydantic validation, dependency injection for database sessions | Flask/Django would require manual async setup, manual docs, manual validation. Raw ASGI too low-level for 53 API endpoints. FastAPI provides essential structure without bloat. |

**Justification Summary**: All three "complex" components are essential and already in production. PJSIP Realtime is a pragmatic exception to Constitution Principle I, justified by production requirements. SQLAlchemy and FastAPI are minimal necessary frameworks that enable rapid development without sacrificing simplicity.

