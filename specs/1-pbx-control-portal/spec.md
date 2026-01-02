# Feature Specification: PBX Control Portal MVP

**Feature Branch**: `1-pbx-control-portal`
**Created**: 2026-01-01
**Status**: Draft
**Input**: User description: "MVP-01: Backend-only PBX control portal for Asterisk 22.7.0 (PJSIP-only)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create User with Extension Allocation (Priority: P1)

System administrators need to create users and automatically provision them with working SIP extensions so new employees can make internal calls immediately without manual Asterisk configuration.

**Why this priority**: Core capability - without user creation and extension allocation, no other functionality is possible. This is the foundation of the entire PBX control system.

**Independent Test**: Can be fully tested by creating a user via API and verifying they receive an extension in the 1000-1999 range stored in the database. Delivers immediate value by enabling automated user provisioning.

**Acceptance Scenarios**:

1. **Given** no users exist in the system, **When** admin calls POST /users with user details, **Then** system allocates extension 1000, stores user in database, and returns user record with assigned extension
2. **Given** extension 1000 is already allocated, **When** admin creates a new user, **Then** system allocates next available extension (1001), stores user, and returns success
3. **Given** 999 extensions are already allocated (1000-1998), **When** admin creates a new user, **Then** system allocates extension 1999 and returns success
4. **Given** all 1000 extensions are allocated (1000-1999), **When** admin attempts to create a new user, **Then** system returns error indicating extension pool exhausted
5. **Given** user data with missing required fields, **When** admin calls POST /users, **Then** system returns validation error listing missing fields

---

### User Story 2 - Apply Configuration to Asterisk (Priority: P1)

System administrators need to apply pending database changes to the live Asterisk server so that newly created users can actually register and make calls through the PBX.

**Why this priority**: Without Apply, user creation is useless - extensions exist only in database but can't register. This completes the MVP loop: create user → apply config → user can call.

**Independent Test**: Can be fully tested by creating users in database (Story 1), calling POST /apply, and verifying generated config files exist at specified paths with correct PJSIP/dialplan syntax. Delivers value by enabling actual telephony functionality.

**Acceptance Scenarios**:

1. **Given** one user exists in database with extension 1000, **When** admin calls POST /apply, **Then** system generates PJSIP config with endpoint+auth+aor for extension 1000, generates dialplan with Dial() for 1000, writes both files atomically, reloads Asterisk, and records audit log
2. **Given** three users exist with extensions 1000, 1001, 1005, **When** admin calls POST /apply, **Then** generated PJSIP config contains three endpoint blocks, dialplan contains three exten entries, files written atomically, Asterisk reloaded, audit logged
3. **Given** Asterisk config generation succeeds but file write fails (permission denied), **When** admin calls POST /apply, **Then** system returns error without corrupting existing config, no partial files written, Asterisk not reloaded
4. **Given** config generation and write succeed but Asterisk reload fails, **When** admin calls POST /apply, **Then** system logs the reload failure, returns error to admin, but new config files remain on disk for manual investigation
5. **Given** no users in database, **When** admin calls POST /apply, **Then** system generates empty/minimal config files and returns success (cleanup scenario)

---

### User Story 3 - List Users (Priority: P2)

System administrators need to view all existing users and their assigned extensions to verify provisioning, troubleshoot user issues, and audit extension allocation.

**Why this priority**: Essential for operations but not blocking MVP functionality. Admins can work without listing if they track users externally, but this significantly improves usability.

**Independent Test**: Can be fully tested by creating several users (Story 1) and calling GET /users to verify all users are returned with correct extension assignments. Delivers operational visibility.

**Acceptance Scenarios**:

1. **Given** three users exist in database, **When** admin calls GET /users, **Then** system returns array of all three users with their extensions, names, and metadata
2. **Given** no users exist in database, **When** admin calls GET /users, **Then** system returns empty array with 200 OK status
3. **Given** database contains 500 users, **When** admin calls GET /users, **Then** system returns all 500 users efficiently (within reasonable time/memory bounds)

---

### User Story 4 - Delete User (Priority: P3)

System administrators need to remove users and free their extensions when employees leave or during cleanup/testing scenarios.

**Why this priority**: Nice-to-have for MVP. Admins can work without deletion initially. Main value is extension pool management and cleanup.

**Independent Test**: Can be fully tested by creating a user, deleting them via DELETE /users/{id}, verifying removal from database and extension returned to pool for reuse. Delivers cleanup capability.

**Acceptance Scenarios**:

1. **Given** user with extension 1005 exists, **When** admin calls DELETE /users/{id}, **Then** system removes user from database, frees extension 1005 for reuse, and returns success
2. **Given** user does not exist, **When** admin calls DELETE /users/{invalid-id}, **Then** system returns 404 error
3. **Given** user is deleted but Apply has not been called, **When** Asterisk config is checked, **Then** deleted user's endpoint still exists in Asterisk until next Apply (eventually consistent)

---

### Edge Cases

- What happens when extension pool (1000-1999) is exhausted? System must reject user creation with clear error message.
- How does system handle Asterisk server being unreachable during Apply? Must fail gracefully, log error, leave database unchanged, and inform admin.
- What happens if two Apply actions are called simultaneously? System must serialize Apply operations to prevent race conditions and config corruption.
- How does system handle malformed user data (invalid characters, SQL injection attempts)? Must validate and sanitize all inputs before database insertion.
- What happens if Postgres database is unavailable? All API calls must fail gracefully with appropriate error messages.
- How does system handle partial Asterisk reload failure (PJSIP succeeds, dialplan fails)? Must log detailed error and notify admin of inconsistent state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store Tenant, User, and Extension entities in PostgreSQL database at host 77.42.28.222
- **FR-002**: System MUST automatically allocate extensions from range 1000-1999 when creating users, selecting lowest available number
- **FR-003**: System MUST provide REST API endpoint POST /users to create new users with automatic extension allocation
- **FR-004**: System MUST provide REST API endpoint POST /apply to trigger Asterisk configuration generation and reload
- **FR-005**: System MUST provide REST API endpoint GET /users to retrieve all users and their assigned extensions
- **FR-006**: System MUST provide REST API endpoint DELETE /users/{id} to remove users and free their extensions
- **FR-007**: System MUST generate PJSIP configuration file at /etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf with endpoint+auth+aor sections for each extension
- **FR-008**: System MUST generate dialplan configuration file at /etc/asterisk/extensions.d/synergycall/generated_routing.conf with [synergy-internal] context and Dial(PJSIP/<ext>,25) for each extension
- **FR-009**: System MUST write all configuration files atomically using write-to-temp-then-rename pattern (no direct overwrites)
- **FR-010**: System MUST NOT use Asterisk Realtime or database-driven configuration (file-based only)
- **FR-011**: System MUST NOT modify core Asterisk configuration files (only write to designated include directories)
- **FR-012**: System MUST reload Asterisk after config generation using commands "asterisk -rx 'pjsip reload'" and "asterisk -rx 'dialplan reload'"
- **FR-013**: System MUST record audit log entry for each Apply action including timestamp, user who triggered it, and outcome
- **FR-014**: System MUST validate user input data before database insertion to prevent injection attacks
- **FR-015**: System MUST handle extension pool exhaustion by rejecting user creation with clear error message when all 1000 extensions are allocated
- **FR-016**: System MUST maintain single default Tenant entity in database (multi-tenancy structure prepared but single tenant enforced in MVP)
- **FR-017**: System MUST connect to Asterisk server at 65.108.92.238 for reload operations
- **FR-018**: System MUST serialize Apply operations to prevent concurrent config generation race conditions
- **FR-019**: System MUST return appropriate HTTP status codes (200 OK, 201 Created, 400 Bad Request, 404 Not Found, 500 Internal Server Error, 503 Service Unavailable)
- **FR-020**: System MUST use environment variables for database credentials and Asterisk server connection details (no hardcoded secrets)

### Key Entities *(include if feature involves data)*

- **Tenant**: Represents organization using the PBX system. Contains tenant ID and metadata. MVP enforces single default tenant. Prepares database structure for future multi-tenancy.

- **User**: Represents a person who can use the PBX. Attributes: unique ID, tenant ID (foreign key), name, email, metadata. Each user gets exactly one Extension. Users are created via admin API and stored in Postgres.

- **Extension**: Represents a SIP extension number allocated to a User. Attributes: extension number (1000-1999), user ID (foreign key), allocation timestamp. Extensions are auto-allocated from available pool when user is created. When user is deleted, extension is freed for reuse.

- **ApplyAuditLog**: Records each Apply action. Attributes: timestamp, triggering admin user, outcome (success/failure), error details if failed, file paths written, Asterisk reload results. Used for troubleshooting and compliance tracking.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrator can create a new user and see their assigned extension number returned in under 2 seconds
- **SC-002**: Administrator can apply configuration changes and have new users able to register SIP extensions within 30 seconds of Apply completing
- **SC-003**: System successfully handles allocation of all 1000 extensions (1000-1999) without duplicates or gaps
- **SC-004**: Generated Asterisk configuration files are syntactically valid and load without errors 100% of the time
- **SC-005**: Apply operation completes end-to-end (generate + write + reload) in under 10 seconds for up to 100 users
- **SC-006**: System maintains data consistency - after Apply, every user in database has corresponding PJSIP endpoint and dialplan entry in generated config files
- **SC-007**: Audit log captures 100% of Apply actions with timestamp, outcome, and error details for failed attempts
- **SC-008**: System rejects invalid user data (missing fields, malformed input) with clear validation error messages 100% of the time
- **SC-009**: Concurrent Apply attempts are serialized without corruption or race conditions in 100% of cases
- **SC-010**: Administrator can retrieve complete user list via GET /users in under 1 second for up to 500 users

## Constraints

### Technical Constraints

- **Asterisk Version**: Must work with Asterisk 22.7.0 installed on Ubuntu at 65.108.92.238
- **SIP Stack**: PJSIP only (chan_sip not used, not supported)
- **Extension Range**: Exactly 1000 extensions available (1000-1999), hard limit
- **Database**: PostgreSQL at 77.42.28.222, schema must be created by portal
- **Network Access**: Portal must have SSH/command access to Asterisk server for reload operations
- **File Paths**: Config files must be written to /etc/asterisk/pjsip.d/synergycall/ and /etc/asterisk/extensions.d/synergycall/
- **Include Configuration**: Core Asterisk files must already have include directives for synergycall directories (manual setup prerequisite)

### Business Constraints

- **MVP Scope**: Backend/API only, no web UI or frontend
- **Single Tenant**: Only one tenant supported in MVP (database prepared for multi-tenant but enforcement is single-tenant)
- **No User Authentication**: MVP assumes trusted admin network, no API authentication required (security hardening deferred to post-MVP)
- **Manual Trunk Configuration**: Inbound trunk context "from-gsm" already configured manually in Asterisk, not managed by portal

### Operational Constraints

- **Explicit Apply**: Configuration changes are NOT automatically applied to Asterisk - admin must call POST /apply explicitly
- **Eventual Consistency**: Database changes (create/delete user) are immediately visible in API but do not affect Asterisk until Apply is called
- **Downtime Risk**: Asterisk reload operations (pjsip reload, dialplan reload) may briefly interrupt active calls - admin responsibility to schedule Apply during low-traffic periods

## Assumptions

- Asterisk server at 65.108.92.238 is accessible from portal host and has required include directories created (/etc/asterisk/pjsip.d/synergycall/, /etc/asterisk/extensions.d/synergycall/)
- Core Asterisk configuration files (pjsip.conf, extensions.conf) already include directives: `#include pjsip.d/synergycall/*.conf` and `#include extensions.d/synergycall/*.conf`
- Portal has SSH access or equivalent command execution capability on Asterisk server to run "asterisk -rx" commands
- PostgreSQL database at 77.42.28.222 is accessible from portal host with credentials provided via environment variables
- Database schema will be created by portal on first run (migrations handled by portal)
- Portal runs in trusted network environment (no API authentication required for MVP)
- Extension numbers 1000-1999 are reserved exclusively for portal-managed users (no manual Asterisk config uses these numbers)
- SIP passwords/secrets for extensions will be auto-generated by portal (random secure passwords)
- Users will configure their SIP clients manually using extension number and auto-generated password (no zero-touch provisioning in MVP)
- Inbound calls from trunk (context from-gsm) will be routed to extensions via separate manual dialplan configuration (not part of MVP)
- PJSIP transport and general settings are configured manually in core Asterisk config (portal only generates endpoint-specific config)

## Dependencies

### External Systems

- **Asterisk 22.7.0**: Core PBX system running on 65.108.92.238, must be operational and accessible
- **PostgreSQL Database**: Must be running at 77.42.28.222 with network access from portal host
- **SSH/Command Access**: Portal requires ability to execute "asterisk -rx" commands on Asterisk host (likely via SSH or similar remote execution mechanism)

### Manual Prerequisites

- Asterisk include directories created: /etc/asterisk/pjsip.d/synergycall/ and /etc/asterisk/extensions.d/synergycall/
- Core Asterisk files modified to include: `#include pjsip.d/synergycall/*.conf` in pjsip.conf and `#include extensions.d/synergycall/*.conf` in extensions.conf
- PJSIP transport configured in core Asterisk config (UDP/TCP listeners on appropriate ports)
- Inbound trunk context "from-gsm" configured manually in Asterisk for external call routing
- Network firewall rules allowing portal → Asterisk (SSH/command access) and portal → PostgreSQL (port 5432)
- Environment variables configured on portal host with database credentials and Asterisk connection details

## Out of Scope

- Web UI or frontend interface (API only)
- User authentication and authorization (trusted network assumed)
- Multi-tenant support enforcement (database structured for it but MVP is single-tenant only)
- SIP client auto-provisioning (users configure phones manually)
- Inbound call routing from trunk to extensions (manual dialplan)
- Outbound call routing and trunk management (manual configuration)
- Call detail records (CDR) or call history
- Voicemail configuration
- IVR or auto-attendant setup
- Conference rooms or call groups
- Extension feature codes (*97 for voicemail, etc.)
- Music on hold configuration
- Call recording
- Real-time call monitoring or presence
- Extension-to-extension calling restrictions
- International dialing permissions
- Emergency services (E911) configuration
- High availability or failover for Asterisk or database
- Backup and disaster recovery automation
- Performance monitoring and alerting
- Rate limiting or abuse prevention on API
- Bulk user import/export
- Extension number customization (always auto-allocated from 1000-1999)
- SIP password reset or rotation (manual database update if needed)
