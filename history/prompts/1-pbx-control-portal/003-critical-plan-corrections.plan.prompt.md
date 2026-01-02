---
id: 003
title: Critical Plan Corrections - Subprocess and Concurrency
stage: plan
date: 2026-01-01
surface: agent
model: claude-sonnet-4-5
feature: 1-pbx-control-portal
branch: 1-pbx-control-portal
user: Ozair Tariq
command: /sp.plan (corrections)
labels: ["plan", "corrections", "subprocess", "concurrency", "simplicity"]
links:
  spec: specs/1-pbx-control-portal/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/1-pbx-control-portal/plan.md
  - specs/1-pbx-control-portal/research.md
  - specs/1-pbx-control-portal/data-model.md
  - specs/1-pbx-control-portal/contracts/api.yaml
  - specs/1-pbx-control-portal/quickstart.md
tests:
  - N/A
---

## Prompt

User provided two critical corrections to the implementation plan:

1. **Don't use SSH (Paramiko) for local apply operations**: Portal will run on same Asterisk server (65.108.92.238), so using SSH to connect to itself is over-engineering. Use subprocess.run() for local execution instead. SSH can be kept as future option for remote setups.

2. **Extension allocation must be concurrency-safe**: The MIN query approach needs proper transaction handling and retry logic to prevent race conditions when two admins create users simultaneously. Need UNIQUE constraint on extension.number and proper transaction isolation with retry.

Both align with Constitution Principle VIII (Simplicity First) and improve reliability.

## Response snapshot

Applied both critical corrections across all planning artifacts:

**Correction 1: Paramiko → subprocess**

Changes made:
- **research.md Decision 3**: Replaced "Paramiko (SSH)" with "subprocess (Python stdlib)"
  - Rationale updated: Co-located deployment, no SSH complexity, stdlib only
  - Implementation pattern added: subprocess.run(["asterisk", "-rx", "pjsip reload"])
  - Future enhancement noted: SSH option if portal moves to separate host

- **plan.md Technical Context**: "Paramiko" → "subprocess (local Asterisk commands)"
  - Summary updated: "Portal runs on Asterisk server (65.108.92.238)"
  - Dependencies updated: removed Paramiko, added subprocess
  - Project structure: src/remote/ → src/asterisk/ (AsteriskReloader)

- **contracts/api.yaml POST /apply**: SSH commands → subprocess commands
  - Description: "Reload Asterisk via local subprocess" with code examples
  - Error examples: SSH timeout → subprocess exit code errors

- **quickstart.md**: Removed all SSH setup steps
  - Prerequisites: Removed SSH access requirement, added Asterisk co-located note
  - .env config: Removed ASTERISK_SSH_* variables
  - Dependencies: Removed paramiko from requirements.txt
  - Troubleshooting: Removed SSH section, updated Asterisk reload errors for local execution
  - Testing: "Mock SSH" → "Mock subprocess"

**Correction 2: Concurrency-safe extension allocation**

Changes made:
- **research.md Decision 5**: Added concurrency safety pattern
  - UNIQUE constraint on extension.number documented
  - Retry logic on IntegrityError added (max 5 retries)
  - Python code example showing transaction + flush + retry pattern

- **data-model.md Extension entity**: Added concurrency safety section
  - UNIQUE constraint emphasized
  - Transaction + retry logic documented
  - Performance notes: "Handles simultaneous allocations without SELECT FOR UPDATE lock contention"

- **plan.md summaries**: Added concurrency safety notes
  - Phase 0: "Concurrency-safe extension allocation" added to key decisions
  - Data Model Summary: "UNIQUE constraint + DB transaction + retry on conflict"

**Constitution Compliance Impact**:
- Principle VIII (Simplicity First) strengthened: subprocess stdlib vs Paramiko dependency
- No new violations introduced
- Concurrency safety improves reliability without adding complexity

## Outcome

- ✅ Impact: Plan simplified (removed SSH complexity) and hardened (concurrency-safe allocation)
- 🧪 Tests: N/A (planning corrections - test mocking updated from SSH to subprocess)
- 📁 Files: Updated plan.md, research.md, data-model.md, contracts/api.yaml, quickstart.md
- 🔁 Next prompts: /sp.tasks ready to proceed with corrected architecture
- 🧠 Reflection: Critical corrections align perfectly with constitution. subprocess approach removes entire failure domain (SSH auth, network, keys). Concurrency safety prevents race conditions in extension allocation. Both improve MVP reliability and simplicity.

## Evaluation notes (flywheel)

- Failure modes observed: None - corrections applied successfully
- Graders run and results (PASS/FAIL): Manual review PASS - all SSH references removed, concurrency pattern documented
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A - corrections incorporated, ready for task generation
