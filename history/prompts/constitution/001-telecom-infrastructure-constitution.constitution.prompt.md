---
id: 001
title: Telecom Infrastructure Constitution
stage: constitution
date: 2026-01-01
surface: agent
model: claude-sonnet-4-5
feature: none
branch: master
user: Ozair Tariq
command: /sp.constitution
labels: ["constitution", "telecom", "safety", "asterisk", "infrastructure"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - N/A
---

## Prompt

/sp.constitution This project is telecom infrastructure; stability and safety override convenience.

Rules:
1) Asterisk remains file-based. Asterisk Realtime (DB-driven SIP/dialplan) is forbidden.
2) The portal must only write generated include files; do not rewrite core Asterisk files except adding include lines if needed.
3) Config writes must be atomic (write temp -> move).
4) Asterisk reloads happen only via explicit Apply action.
5) No features outside the current specification.
6) No frontend in MVP unless specified.
7) Never hardcode secrets; use env vars.
8) Prefer simplest implementation that meets requirements.

## Response snapshot

Created PBX Client Web Constitution v1.0.0 with 8 core principles focused on telecom infrastructure stability and safety:

**Core Principles**:
I. File-Based Asterisk Configuration (NON-NEGOTIABLE) - No database-driven configs
II. Isolated Configuration Generation - Portal writes only include files
III. Atomic File Operations - Write temp → move pattern mandatory
IV. Explicit Apply Actions - No automatic Asterisk reloads
V. Strict Scope Adherence - Only implement specified features
VI. No Frontend in MVP - Backend/API only unless UI specified
VII. No Hardcoded Secrets - Environment variables mandatory
VIII. Simplicity First - YAGNI principle enforced

**Additional Sections**:
- Technology Constraints (Platform, Security, Deployment)
- Development Workflow (Implementation, Review, Quality Gates)
- Governance (Amendment procedure, versioning, compliance)

All 8 user-provided rules transformed into testable, declarative principles with rationale explaining the telecom infrastructure context.

## Outcome

- ✅ Impact: Constitution v1.0.0 created, establishing foundational governance for PBX Client Web project
- 🧪 Tests: N/A (documentation artifact)
- 📁 Files: Created/updated .specify/memory/constitution.md with sync report
- 🔁 Next prompts: /sp.specify <feature> to create first feature specification adhering to constitution
- 🧠 Reflection: Constitution successfully captures telecom safety requirements with clear, enforceable principles that prioritize stability over convenience

## Evaluation notes (flywheel)

- Failure modes observed: None - constitution creation successful
- Graders run and results (PASS/FAIL): Manual validation PASS - all placeholders filled, no bracketed tokens, principles declarative and testable
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A - baseline constitution established
