<!--
Sync Impact Report:
- Version change: [NEW] → 1.0.0
- Initial constitution creation for PBX Client Web project
- Principles added: 8 core principles for telecom infrastructure stability
- Templates status:
  ✅ plan-template.md - Constitution Check section compatible
  ✅ spec-template.md - Requirements sections compatible
  ✅ tasks-template.md - Task organization compatible
- No follow-up TODOs
-->

# PBX Client Web Constitution

## Core Principles

### I. File-Based Asterisk Configuration (NON-NEGOTIABLE)

Asterisk MUST remain file-based. Asterisk Realtime (database-driven SIP/dialplan configuration) is
FORBIDDEN. This ensures configuration is version-controlled, auditable, and recoverable.

**Rationale**: File-based configuration provides clear versioning, simple rollback, and transparent
change tracking essential for telecom infrastructure stability. Database-driven configs introduce
hidden state that's harder to debug and recover from failures.

### II. Isolated Configuration Generation

The portal MUST only write generated include files. Core Asterisk configuration files MUST NOT be
rewritten except to add include directives when absolutely necessary.

**Rationale**: Protects core telephony system configuration from portal bugs. If the portal fails,
core Asterisk continues operating. Include files provide clean separation between manual and
generated configuration.

### III. Atomic File Operations

All configuration file writes MUST be atomic: write to temporary file, then move/rename to final
location. No direct overwrites of active configuration.

**Rationale**: Prevents partial writes from corrupting active configuration. Atomic operations
ensure Asterisk never reads incomplete or corrupted config files, maintaining service stability.

### IV. Explicit Apply Actions

Asterisk reloads MUST happen only via explicit Apply action initiated by user. No automatic reloads
on configuration change.

**Rationale**: Telecom infrastructure changes require human review and deliberate action.
Auto-reloads risk service disruption from untested changes. Explicit apply gives operators control
over when changes take effect.

### V. Strict Scope Adherence

No features outside the current specification are permitted. No speculative features, no
"nice-to-haves," no premature optimization.

**Rationale**: Telecom systems demand predictability. Every feature is a potential failure point.
Unspecified features bypass review and testing, introducing risk without validated need.

### VI. No Frontend in MVP

No frontend user interface in MVP unless explicitly specified in feature requirements. Portal
operates via API/CLI only until UI is formally specified.

**Rationale**: Frontend adds complexity (auth, session management, input validation, XSS, CSRF).
MVP focuses on core backend reliability. UI added only when requirements are clear and tested.

### VII. No Hardcoded Secrets

Credentials, API keys, passwords, tokens MUST use environment variables. Never commit secrets to
version control. Use `.env` files (gitignored) or system environment.

**Rationale**: Security fundamental. Hardcoded secrets in code create audit trail nightmares and
credential rotation complexity. Environment variables allow secure deployment without code changes.

### VIII. Simplicity First

Prefer the simplest implementation that meets requirements. No abstractions without proven need.
No frameworks unless essential. YAGNI (You Aren't Gonna Need It) is law.

**Rationale**: In telecom infrastructure, complexity is the enemy of reliability. Simple code is
debuggable, auditable, and maintainable. Complex abstractions hide bugs and make troubleshooting
harder under production pressure.

## Technology Constraints

### Platform Requirements

- **Asterisk Version**: File-based configuration (no Realtime)
- **Config Management**: Include-based architecture
- **File Operations**: Atomic writes (temp → move pattern)
- **Reload Strategy**: Manual, explicit apply only

### Security Requirements

- **Secrets Management**: Environment variables only (`.env` for development, system env for production)
- **Configuration Access**: Portal writes to designated include directories only
- **Core Config Protection**: No direct writes to core Asterisk files
- **Audit Trail**: All config changes logged with user/timestamp

### Deployment Constraints

- **MVP Scope**: Backend/API only unless frontend explicitly specified
- **Change Control**: Explicit apply action required for any Asterisk reload
- **Rollback Strategy**: File-based configs enable simple version control rollback
- **Testing**: Changes tested in isolation before apply

## Development Workflow

### Feature Implementation Rules

1. **Spec Compliance**: Implement only what's in the current specification
2. **Testing Gates**: Test configuration generation in isolation before Asterisk integration
3. **Atomic Operations**: All file writes use temp → move pattern
4. **No Auto-Reload**: Never trigger Asterisk reload without explicit user action
5. **Simplicity Check**: Justify any abstraction or framework beyond stdlib

### Code Review Requirements

1. **Constitution Compliance**: Verify all 8 principles are honored
2. **Scope Check**: Confirm no features beyond specification
3. **Security Check**: Verify no hardcoded secrets, atomic file writes
4. **Simplicity Check**: Challenge unnecessary complexity

### Quality Gates

1. **File Operations**: All config writes are atomic
2. **Asterisk Isolation**: Core config files untouched (except include directives)
3. **Manual Control**: No automatic reloads detected
4. **Secret Scanning**: No credentials in code or version control

## Governance

This constitution supersedes all other development practices. All code, design decisions, and
features MUST comply with these principles.

**Amendment Procedure**:
- Proposed changes require documentation of rationale and impact analysis
- Constitution changes increment version (see Versioning Policy below)
- All dependent templates and documentation must be updated for consistency
- Team approval required for any principle modification or removal

**Versioning Policy**:
- **MAJOR** (X.0.0): Backward-incompatible changes (principle removal/redefinition)
- **MINOR** (1.X.0): New principle added or material expansion of existing principle
- **PATCH** (1.0.X): Clarifications, wording improvements, non-semantic refinements

**Compliance Review**:
- All PRs/reviews must verify adherence to all 8 principles
- Complexity must be explicitly justified if it violates Principle VIII (Simplicity First)
- Constitution violations block merge unless amendment is approved first

**Runtime Guidance**:
See `CLAUDE.md` for agent-specific development guidance and execution workflows.

**Version**: 1.0.0 | **Ratified**: 2026-01-01 | **Last Amended**: 2026-01-01
