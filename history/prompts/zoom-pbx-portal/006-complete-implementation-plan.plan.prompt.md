---
id: 006
title: Complete Implementation Plan
stage: plan
date: 2026-01-05
surface: agent
model: claude-sonnet-4.5
feature: zoom-pbx-portal
branch: 001-zoom-pbx-portal
user: Ozair Tariq
command: /sp.plan
labels: ["planning", "architecture", "data-model", "api-contracts", "quickstart"]
links:
  spec: specs/001-zoom-pbx-portal/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-zoom-pbx-portal/plan.md
  - specs/001-zoom-pbx-portal/research.md
  - specs/001-zoom-pbx-portal/data-model.md
  - specs/001-zoom-pbx-portal/contracts/openapi.yaml
  - specs/001-zoom-pbx-portal/quickstart.md
  - CLAUDE.md
tests:
  - Constitution Check: 1 justified violation (PJSIP Realtime with amendment proposal)
  - Technical Context: All fields filled, no NEEDS CLARIFICATION markers
  - Data Model: 9 entities with complete schemas, relationships, validation rules
  - API Contracts: 53+ endpoints with request/response schemas
  - Quickstart: 15-step guide with verification tests
---

## Prompt

User triggered `/sp.plan` command to create a comprehensive implementation plan for the Zoom-Style PBX Management Portal specification.

The `/sp.plan` workflow requires:
1. Setup: Run `.specify/scripts/powershell/setup-plan.ps1 -Json` to initialize
2. Load context: Read feature spec, constitution, plan template
3. Fill plan.md: Technical Context, Constitution Check, Project Structure, Complexity Tracking
4. Phase 0: Generate research.md (resolve NEEDS CLARIFICATION items, establish best practices)
5. Phase 1: Generate data-model.md, contracts/openapi.yaml, quickstart.md, update agent context
6. Phase 2: Stop and report completion

The plan is based on the specification from `specs/001-zoom-pbx-portal/spec.md` which defines:
- 8 prioritized user stories (P1-P3)
- 53 functional requirements across 9 categories
- 28 measurable success criteria
- Multi-tenant PBX management with DID routing, devices, policies, self-service

## Response snapshot

Completed all phases of `/sp.plan` workflow:

**Phase 0: Research (research.md - 665 lines)**
- Resolved 10 major technical decisions with implementation patterns
- Decision 1: DID Routing - Hybrid database + generated dialplan (not AstDB)
- Decision 2: Multi-Device SIP - Unique SIP username per device, shared AOR
- Decision 3: SIP Password Encryption - Fernet symmetric encryption (reversible)
- Decision 4: Outbound Policy Enforcement - Dialplan-based pattern matching
- Decision 5: JWT Authentication & RBAC - 4 roles with decorator-based enforcement
- Decision 6: AMI Integration - Persistent connection with reconnect logic
- Decision 7: Apply Workflow Validation - Pre-apply validation phase
- Decision 8: Database Migrations - Alembic with 7 sequential migrations
- Decision 9: Frontend Integration - Extend existing static HTML/CSS/JS
- Decision 10: Performance Optimization - Strategic indexing, pagination, denormalization

**Phase 1: Design & Contracts**

**data-model.md (comprehensive entity definitions)**:
- **Tenant**: Multi-tenant isolation with extension ranges (ext_min, ext_max, ext_next pointer)
- **User**: Auto-assigned extensions, RBAC roles (4 levels), self-service settings (DND, forward, voicemail)
- **Device**: Multi-device support with unique SIP credentials (sip_username, sip_password_encrypted)
- **DID**: Inbound routing to 6 destination types (USER, RING_GROUP, IVR, QUEUE, VOICEMAIL, EXTERNAL)
- **Trunk**: SIP trunks with 2 auth modes (registration, ip_auth)
- **OutboundPolicy**: Pattern-based calling rules with trunk failover (rules_json schema)
- **ApplyJob**: Configuration apply audit trail (5 states: PENDING, RUNNING, SUCCESS, FAILED, ROLLED_BACK)
- **AuditLog**: Immutable change tracking (before_json, after_json)
- **Extension**: Auto-allocated via tenant.ext_next pointer (O(1) allocation algorithm)

Each entity includes:
- PostgreSQL schema with all fields, types, constraints
- Relationships and foreign keys
- Validation rules and check constraints
- State transitions
- Indexes for performance
- Security considerations (password hashing, encryption)

**contracts/openapi.yaml (OpenAPI 3.0 specification)**:
- **Authentication**: Login, refresh token, logout
- **Tenants**: CRUD operations (platform admin only)
- **Users**: CRUD with auto-extension allocation
- **Devices**: CRUD with SIP password encryption
- **DIDs**: CRUD with E.164 validation
- **Trunks**: CRUD with registration status
- **Outbound Policies**: CRUD with regex pattern validation
- **Apply**: Preview, execute, job history, automatic rollback
- **Self-Service**: DND toggle, call forwarding, voicemail PIN change, greeting upload
- **Diagnostics**: Device registration status (AMI queries), trunk status, health check
- **Audit**: Query logs with filtering (entity_type, action, actor, timestamp)

Total: 53+ endpoints with complete request/response schemas, error responses, authentication requirements

**quickstart.md (15-step developer guide)**:
1. Clone repository
2. Install dependencies (Python 3.12, PostgreSQL, MariaDB, Asterisk)
3. Database setup (PostgreSQL + MariaDB PJSIP Realtime tables)
4. Environment configuration (.env with 20+ variables)
5. Database migrations (Alembic upgrade head)
6. Asterisk configuration (AMI, PJSIP Realtime, dialplan includes)
7. Seed database (demo tenant + admin user)
8. Start development server (uvicorn)
9. Verify installation (health check, login, create user, create device, apply)
10. Test SIP registration (configure softphone, check device status)
11. Access frontend (web UI)
12. Run tests (pytest with coverage)
13. Troubleshooting (5 common issues with fixes)
14. Development workflow (feature branches, migrations, debugging)
15. Production deployment notes (security checklist)

**Agent Context Update**:
- Updated CLAUDE.md with project tech stack
- Added language: Python 3.12
- Added frameworks: FastAPI 0.104+, SQLAlchemy 2.0+, PostgreSQL 16.11, MariaDB, Asterisk 22.7.0

**Constitution Check Results**:
- **Principle I (File-Based Config)**: ⚠️ VIOLATION - JUSTIFIED
  - Violation: PJSIP Realtime uses MariaDB for dynamic endpoints
  - Justification: Already in production, enables multi-device hot-swapping without reloads, limited to SIP endpoints only
  - Proposed Amendment: Add exception clause for PJSIP endpoint registration via Realtime
- **Principles II-VIII**: ✅ ALL PASS
  - Isolated config generation (portal-owned includes only)
  - Atomic file operations (temp → move pattern)
  - Explicit apply actions (user-triggered with advisory locks)
  - Strict scope adherence (no speculative features)
  - Frontend exception granted (explicitly specified in spec)
  - No hardcoded secrets (.env pattern)
  - Simplicity first (minimal frameworks: FastAPI, SQLAlchemy)

**Commits**:
1. Commit 4e3da41: Phase 0 artifacts (plan.md + research.md)
2. Commit b4f137d: Phase 1 artifacts (data-model.md + contracts/openapi.yaml + quickstart.md + CLAUDE.md)

## Outcome

- ✅ Impact: Complete implementation plan created for Zoom-style PBX portal with architecture decisions, data model (9 entities), API contracts (53+ endpoints), and developer quickstart guide. Ready for task breakdown and implementation.
- 🧪 Tests: Constitution check completed (1 justified violation with amendment proposal), Technical context validated (all fields filled, no NEEDS CLARIFICATION), Data model validated (complete schemas with relationships and constraints), API contracts validated (complete request/response schemas for all endpoints)
- 📁 Files: Created plan.md (292 lines), research.md (665 lines), data-model.md (850+ lines), contracts/openapi.yaml (1500+ lines), quickstart.md (800+ lines); Updated CLAUDE.md
- 🔁 Next prompts: "/sp.tasks" to generate implementation task breakdown, or begin implementing P1 user stories (User Provisioning, DID Routing, Safe Apply)
- 🧠 Reflection: Planning phase successfully completed with comprehensive technical decisions. Key architectural patterns established: (1) Hybrid DID routing (database + dialplan) for debuggability, (2) Multi-device SIP with unique credentials per device for granular control, (3) Pre-apply validation phase to prevent Asterisk downtime, (4) Fernet encryption for reversible SIP passwords. Constitution violation (PJSIP Realtime) thoroughly justified with pragmatic reasoning and amendment proposal. Data model provides complete foundation with 9 entities, foreign key relationships, validation constraints, and performance indexes. API contracts cover all 53 functional requirements with proper authentication, authorization, and error handling. Quickstart guide enables developers to verify end-to-end workflow in 15 minutes. Ready to proceed with /sp.tasks for detailed implementation breakdown.

## Evaluation notes (flywheel)

- Failure modes observed: None - all phases completed successfully. Initial attempt to run PowerShell script failed on Linux environment, but successfully used Windows PowerShell via WSL interop.
- Graders run and results (PASS/FAIL):
  - Constitution Check: PASS (1 violation justified with amendment proposal)
  - Technical Context: PASS (all fields filled, no NEEDS CLARIFICATION)
  - Data Model: PASS (9 entities complete with schemas, relationships, validation)
  - API Contracts: PASS (53+ endpoints with complete schemas)
  - Quickstart Guide: PASS (15-step guide with verification tests)
- Prompt variant (if applicable): Standard /sp.plan workflow
- Next experiment (smallest change to try): When generating tasks.md via /sp.tasks, ensure tasks reference specific data model entities and API endpoints from planning artifacts. This will create tighter coupling between plan and implementation tasks, reducing ambiguity and improving task completeness.
