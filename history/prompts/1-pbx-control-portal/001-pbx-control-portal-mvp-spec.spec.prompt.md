---
id: 001
title: PBX Control Portal MVP Specification
stage: spec
date: 2026-01-01
surface: agent
model: claude-sonnet-4-5
feature: 1-pbx-control-portal
branch: 1-pbx-control-portal
user: Ozair Tariq
command: /sp.specify
labels: ["spec", "pbx", "asterisk", "pjsip", "mvp", "user-management"]
links:
  spec: specs/1-pbx-control-portal/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/1-pbx-control-portal/spec.md
  - specs/1-pbx-control-portal/checklists/requirements.md
tests:
  - N/A
---

## Prompt

/sp.specify MVP-01: Backend-only PBX control portal for Asterisk 22.7.0 (PJSIP-only)

Environment:
- Asterisk host: 65.108.92.238 (Ubuntu), Asterisk 22.7.0
- SIP stack: PJSIP only (chan_sip not used)
- Inbound trunk context already configured: from-gsm
- Postgres DB host: 77.42.28.222

MVP objectives:
1) Create User (admin API) and automatically allocate an Extension from range 1000–1999.
2) Store Tenant (single default), Users, Extensions in Postgres.
3) Implement Apply action (admin API) that:
   - reads current DB state
   - generates Asterisk include files:
     - /etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf
     - /etc/asterisk/extensions.d/synergycall/generated_routing.conf
   - writes files atomically (temp -> rename)
   - reloads Asterisk:
     - asterisk -rx "pjsip reload"
     - asterisk -rx "dialplan reload"
   - records an audit log entry for apply

Asterisk generation rules:
- Do NOT use Asterisk Realtime.
- Do NOT rewrite core Asterisk files (only generate include files).
- Generated PJSIP must create endpoint+auth+aor per extension.
- Generated dialplan must create context [synergy-internal] with exten dialing:
  exten => <ext>,1,Dial(PJSIP/<ext>,25)
  same => n,Hangup()

APIs required (MVP):
- POST /users (create user)
- POST /apply (apply config)
- GET /users (list users)
- DELETE /users/{id} (delete user)

## Response snapshot

Created comprehensive feature specification for PBX Control Portal MVP on branch 1-pbx-control-portal.

**Specification Structure**:
- 4 prioritized user stories (P1: Create User, P1: Apply Config, P2: List Users, P3: Delete User)
- 20 functional requirements covering all MVP objectives
- 10 measurable success criteria (performance, reliability, consistency)
- Complete constraints (technical, business, operational)
- 13 documented assumptions
- Dependencies and manual prerequisites identified
- 28 items explicitly marked out of scope

**Key Design Decisions**:
- Extension auto-allocation from 1000-1999 pool (lowest available)
- Atomic file writes (temp → rename) per constitution
- Explicit Apply pattern (eventual consistency model)
- Single default tenant in MVP (DB prepared for multi-tenant)
- No API authentication (trusted network assumption)
- Serialized Apply operations to prevent race conditions

**Constitution Compliance**:
✅ File-based Asterisk (no Realtime)
✅ Isolated config generation (include files only)
✅ Atomic file operations specified
✅ Explicit Apply actions (no auto-reload)
✅ Strict scope adherence (no features beyond spec)
✅ No frontend in MVP
✅ Environment variables for secrets
✅ Simplicity first (minimal abstractions)

**Validation Results**:
All checklist items PASS - specification ready for /sp.plan

## Outcome

- ✅ Impact: Complete, validated feature specification created for PBX control portal MVP
- 🧪 Tests: N/A (specification artifact - testing criteria defined in success criteria)
- 📁 Files: Created specs/1-pbx-control-portal/spec.md and checklists/requirements.md
- 🔁 Next prompts: /sp.plan to create implementation plan, or /sp.clarify if stakeholder refinement needed
- 🧠 Reflection: Specification successfully captures all MVP requirements while maintaining constitution compliance. Zero [NEEDS CLARIFICATION] markers - all details specified or reasonable defaults assumed. Ready for planning phase.

## Evaluation notes (flywheel)

- Failure modes observed: None - specification creation successful
- Graders run and results (PASS/FAIL): Quality checklist validation PASS - all 14 items passed (content quality, requirement completeness, feature readiness)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A - baseline specification established, proceed to planning
