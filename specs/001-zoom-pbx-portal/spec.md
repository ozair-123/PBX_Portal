# Feature Specification: Zoom-Style PBX Management Portal

**Feature Branch**: `001-zoom-pbx-portal`
**Created**: 2026-01-04
**Status**: Draft
**Input**: User description: "Build a Zoom-like PBX management experience on top of Asterisk that treats Users as the core object, automatically assigns Extensions, routes inbound calls by DID → Destination mapping, provides safe Apply workflow, and allows end user self-service"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - User Provisioning with Auto-Extension Assignment (Priority: P1)

As a **tenant admin**, I need to create user accounts that automatically receive phone extensions so that new employees can immediately register their desk phones without manual SIP configuration.

**Why this priority**: This is the foundational capability - without users and extensions, no other PBX functionality is possible. Delivers immediate value by enabling phone service for end users.

**Independent Test**: Can be fully tested by creating a user through the admin portal and verifying they receive an extension number and can register a SIP device using auto-generated credentials. Delivers standalone value as users can make/receive extension-to-extension calls.

**Acceptance Scenarios**:

1. **Given** a tenant admin is logged into the portal, **When** they create a new user with name and email, **Then** the system automatically assigns the next available extension (e.g., 1000, 1001, 1002) from the tenant's extension range
2. **Given** a user has been created with an auto-assigned extension, **When** the admin views user details, **Then** they see the extension number, SIP username, and auto-generated SIP password
3. **Given** a tenant has extensions 1000-1999 allocated and 1002 is the next available, **When** admin creates a user, **Then** the user receives extension 1002 and the next pointer advances to 1003
4. **Given** a user account exists with extension 1005, **When** the user configures their desk phone with the SIP credentials, **Then** the phone successfully registers and shows as "Registered" in the portal
5. **Given** two users with extensions 1001 and 1002 are registered, **When** user 1001 dials 1002, **Then** user 1002's phone rings and they can answer the call

---

### User Story 2 - Inbound DID Routing to Users (Priority: P2)

As a **tenant admin**, I need to assign external phone numbers (DIDs) to users so that incoming calls from the public network reach the correct employee's desk phone.

**Why this priority**: Enables external callers to reach users, which is essential for business communication. Depends on User Story 1 (users must exist first) but is the next critical capability for a functional phone system.

**Independent Test**: Can be tested by assigning a DID to a user and making an external call to that DID, verifying it rings the user's registered device. Delivers standalone value as users can now receive external calls.

**Acceptance Scenarios**:

1. **Given** a tenant admin has added DID +1-555-0100 to the portal, **When** they assign it to user John (extension 1001) with destination type "USER", **Then** the DID routing table shows +1-555-0100 → User: John (1001)
2. **Given** DID +1-555-0100 is assigned to extension 1001, **When** an external caller dials +1-555-0100, **Then** extension 1001's registered device rings
3. **Given** DID +1-555-0200 is not assigned to any user, **When** an external caller dials +1-555-0200, **Then** the call routes to the tenant's default inbound destination (e.g., main receptionist or voicemail)
4. **Given** a tenant admin is viewing the Phone Numbers page, **When** they click "Assign DID", **Then** they see a dropdown of all users and can select the destination user
5. **Given** DID +1-555-0100 was assigned to extension 1001, **When** admin reassigns it to extension 1002, **Then** subsequent calls to +1-555-0100 ring extension 1002 instead

---

### User Story 3 - Safe Configuration Apply with Rollback (Priority: P1)

As a **tenant admin**, I need to apply pending changes (users, DIDs, policies) to the live Asterisk PBX safely so that configuration errors don't cause phone system downtime.

**Why this priority**: Critical for production reliability - prevents a single mistake from breaking the entire phone system. Must be part of MVP to ensure safe operations from day one.

**Independent Test**: Can be tested by making changes in the portal (e.g., creating users), clicking "Apply", and verifying Asterisk is reloaded without downtime. If an error occurs (e.g., invalid config), verify the system rolls back to the last working state. Delivers standalone value by providing confidence in making changes.

**Acceptance Scenarios**:

1. **Given** admin has created 3 new users in the portal (pending state), **When** they click "Apply Configuration", **Then** the system generates Asterisk configs, backs up the previous configs, writes new configs, reloads Asterisk modules, and shows "Apply Successful"
2. **Given** the apply operation is in progress, **When** a second admin tries to apply, **Then** they receive an error "Another apply operation is currently in progress"
3. **Given** admin creates a user with extension 1005 but extension 1005 already exists in Asterisk, **When** they click "Apply", **Then** the system detects the conflict, shows "Apply Failed: Duplicate extension 1005", and does NOT reload Asterisk
4. **Given** the apply operation generates invalid Asterisk config syntax, **When** the reload command fails, **Then** the system automatically restores the previous working config files and shows "Apply Failed: Rollback completed"
5. **Given** an apply operation completed (success or failure), **When** admin views Apply History, **Then** they see a log entry with timestamp, outcome, files changed, and error details if applicable

---

### User Story 4 - Device Management for Multi-Device Users (Priority: P2)

As a **tenant admin**, I need to allow users to have multiple SIP devices (desk phone, softphone, mobile app) so that employees can use their extension from any location.

**Why this priority**: Enables modern work flexibility (desk + mobile + softphone). Depends on User Story 1 but adds significant value for hybrid work environments.

**Independent Test**: Can be tested by creating multiple devices for a single user (e.g., desk phone + mobile app) and verifying both can register simultaneously and receive calls. Delivers standalone value by enabling multi-device usage.

**Acceptance Scenarios**:

1. **Given** user John has extension 1001, **When** admin creates two devices (Desk Phone, Mobile App) for John, **Then** both devices receive unique SIP credentials (e.g., 1001-desk, 1001-mobile)
2. **Given** John has two registered devices, **When** someone calls extension 1001, **Then** both devices ring simultaneously
3. **Given** admin is viewing John's device list, **When** they check device status, **Then** they see "Registered" or "Unregistered" for each device with last-seen timestamp
4. **Given** John's mobile device loses network, **When** admin views device status, **Then** they see the mobile device as "Unregistered" but the desk phone remains "Registered"
5. **Given** admin deletes John's mobile device, **When** John tries to register with the old mobile credentials, **Then** registration is rejected

---

### User Story 5 - Outbound Calling with Policy Enforcement (Priority: P2)

As a **tenant admin**, I need to control which users can make international/premium calls and route outbound calls through configured trunks so that the organization manages telecom costs and usage.

**Why this priority**: Essential for cost control and compliance. Depends on User Story 1 and configured trunks, but is critical for production use to prevent unauthorized international calling.

**Independent Test**: Can be tested by configuring an outbound policy that blocks international calls, then having a user attempt to dial an international number and verifying it's rejected. Delivers standalone value by enabling cost control.

**Acceptance Scenarios**:

1. **Given** tenant has an outbound policy "Local Only" (allows 1NXXNXXXXXX patterns), **When** user 1001 dials 911, **Then** the call is allowed and routes through the configured trunk
2. **Given** user 1001 is assigned "Local Only" policy, **When** they dial +44-20-1234-5678 (UK number), **Then** the call is blocked and they hear "This call is not permitted"
3. **Given** tenant has two trunks (Trunk A priority 1, Trunk B priority 2), **When** user makes an outbound call, **Then** the system attempts Trunk A first, and only uses Trunk B if Trunk A fails
4. **Given** outbound policy includes number normalization rule (strip leading 1), **When** user dials 1-555-0100, **Then** the system sends 5550100 to the trunk
5. **Given** admin is creating an outbound policy, **When** they use the test tool to simulate dialing +1-555-0100, **Then** the system shows which trunk would be selected and whether the call would be allowed

---

### User Story 6 - End User Self-Service Features (Priority: P3)

As an **end user**, I need to control my own phone settings (DND, call forwarding, voicemail PIN) without contacting IT so that I can manage my availability and preferences independently.

**Why this priority**: Reduces IT support burden and empowers users. Lower priority because users can initially ask admins to make these changes, but significantly improves user experience.

**Independent Test**: Can be tested by logging in as an end user, enabling DND, and verifying incoming calls go to voicemail. Delivers standalone value by enabling user autonomy.

**Acceptance Scenarios**:

1. **Given** end user John logs into the portal, **When** he toggles "Do Not Disturb" to ON, **Then** incoming calls to his extension immediately go to voicemail
2. **Given** John has DND enabled, **When** he dials another extension, **Then** his outbound calls work normally (DND only affects inbound)
3. **Given** John wants calls forwarded to his mobile, **When** he sets "Call Forward" to +1-555-9999, **Then** all incoming calls to his extension ring +1-555-9999 instead
4. **Given** John's voicemail PIN is 1234, **When** he changes it to 5678, **Then** he can only access voicemail using the new PIN 5678
5. **Given** John wants a custom voicemail greeting, **When** he uploads an audio file (MP3/WAV), **Then** callers hear his custom greeting instead of the default

---

### User Story 7 - Tenant Management for Multi-Tenant Deployments (Priority: P3)

As a **platform admin**, I need to manage multiple tenants (companies) on a single Asterisk server so that each tenant has isolated extensions, users, and policies.

**Why this priority**: Enables SaaS/multi-tenant deployment model. Lower priority for MVP if starting with single tenant, but critical for scalability and service provider use cases.

**Independent Test**: Can be tested by creating two tenants with overlapping extension ranges (Tenant A: 1000-1999, Tenant B: 1000-1999), creating users in each, and verifying extension 1000 in Tenant A is completely isolated from extension 1000 in Tenant B. Delivers standalone value by enabling multi-tenant hosting.

**Acceptance Scenarios**:

1. **Given** platform admin creates Tenant "ACME Corp" with extension range 1000-1499, **When** ACME admin creates users, **Then** extensions are auto-assigned starting from 1000
2. **Given** Tenant A has user with extension 1001 and Tenant B has user with extension 1001, **When** Tenant A user 1001 dials 1002, **Then** they reach Tenant A's extension 1002 (not Tenant B)
3. **Given** platform admin suspends Tenant "ACME Corp", **When** any ACME user tries to make a call, **Then** the call is blocked with "Service suspended"
4. **Given** each tenant has independent outbound policies, **When** Tenant A user makes an international call, **Then** Tenant A's policy applies (not Tenant B's)
5. **Given** platform admin views tenant list, **When** they see each tenant, **Then** they see total users, total DIDs, extension range, and status (active/suspended)

---

### User Story 8 - Diagnostics and Real-Time Status (Priority: P3)

As a **tenant admin or support user**, I need to view real-time device registration status and endpoint health so that I can troubleshoot user phone issues without accessing Asterisk CLI.

**Why this priority**: Reduces troubleshooting time and enables non-technical admins to diagnose issues. Lower priority because initial deployment can rely on CLI for troubleshooting, but significantly improves operational efficiency.

**Independent Test**: Can be tested by registering a device, viewing the Diagnostics page, and verifying it shows as "Registered" with correct IP address and user agent. Then unplug the device's network and verify it shows as "Unregistered" within 60 seconds. Delivers standalone value by enabling self-service troubleshooting.

**Acceptance Scenarios**:

1. **Given** admin views the Devices page, **When** they refresh the page, **Then** they see real-time registration status (Registered/Unregistered) for each device
2. **Given** user's desk phone is registered, **When** admin views device details, **Then** they see IP address, contact URI, user agent string, and last registration timestamp
3. **Given** admin suspects Asterisk is down, **When** they view System Health, **Then** they see Asterisk status (Running/Stopped), database connectivity, disk space, and last health check timestamp
4. **Given** admin needs to troubleshoot outbound calling, **When** they view Trunk status, **Then** they see each trunk's registration status (for registration-based trunks) and reachability
5. **Given** support user (read-only role) logs in, **When** they view diagnostics pages, **Then** they can see all status information but cannot make changes or apply config

---

### Edge Cases

- **What happens when tenant's extension pool is exhausted?** System prevents creating new users and shows "Extension pool exhausted: increase max extension range" error.
- **What happens when user is deleted but their extension is still registered?** Apply operation removes the endpoint from Asterisk, causing immediate un-registration.
- **What happens when two admins modify the same DID simultaneously?** Last-write-wins with audit log showing both changes. Conflict detection is not implemented in MVP.
- **What happens when Asterisk is unreachable during Apply?** Apply operation fails with "Cannot connect to Asterisk AMI" error, no changes are made, previous config remains active.
- **What happens when DID format is invalid (not E.164)?** System validates DID format on input and rejects with "Invalid DID format: must be E.164 (+1234567890)" error.
- **What happens when user tries to forward calls to an invalid number?** System validates phone number format; if invalid, rejects with error. If valid but unreachable, calls fail silently (carrier handles).
- **What happens when trunk credentials are incorrect?** Asterisk fails to register/authenticate with trunk. Outbound calls through that trunk fail. System shows trunk status as "Registration Failed" in diagnostics.
- **What happens when multiple devices for one user ring simultaneously and one answers?** All other devices stop ringing immediately (standard SIP forking behavior handled by Asterisk).
- **What happens when user uploads a 100MB voicemail greeting file?** System validates file size (max 5MB) and format (MP3/WAV) on upload, rejecting oversized files.
- **What happens during apply if Asterisk reload succeeds but database commit fails?** System attempts to reload Asterisk back to previous state. This is a rare edge case that may require manual intervention if rollback fails.

## Requirements *(mandatory)*

### Functional Requirements

#### User & Extension Management

- **FR-001**: System MUST automatically assign the next available extension from tenant's configured range (ext_min to ext_max) when creating a user
- **FR-002**: System MUST prevent duplicate extensions within the same tenant
- **FR-003**: System MUST generate unique SIP credentials (username, password) for each device
- **FR-004**: System MUST allow soft-delete of users (retain audit history, optionally release extension back to pool)
- **FR-005**: System MUST support user status (active, suspended) where suspended users cannot make outbound calls
- **FR-006**: System MUST optionally create voicemail mailbox when creating a user (toggle on user creation form)

#### Device Management

- **FR-007**: System MUST allow multiple devices per user (one user can have 0..N devices)
- **FR-008**: System MUST store device properties: label, sip_username, sip_password, transport (UDP/TCP), NAT flags, codec preferences
- **FR-009**: System MUST query Asterisk for real-time device registration status (registered/unregistered, contact URI, last-seen)
- **FR-010**: System MUST encrypt SIP passwords at rest in the database
- **FR-011**: System MUST never log SIP passwords in audit logs or system logs

#### DID Routing

- **FR-012**: System MUST store DID objects with: did_number (E.164 format), label, destination_type (USER, RING_GROUP, IVR, QUEUE, VOICEMAIL, EXTERNAL), destination_target
- **FR-013**: System MUST validate DID numbers are in E.164 format (+[country][area][number])
- **FR-014**: System MUST route inbound calls to the configured destination based on DID lookup
- **FR-015**: System MUST route calls to tenant's default_inbound_destination when DID is not found in routing table
- **FR-016**: System MUST support reassigning DIDs from one destination to another without downtime

#### Outbound Policy & Trunks

- **FR-017**: System MUST enforce outbound policies with dial pattern rules (prefix/regex matching)
- **FR-018**: System MUST support trunk priority lists (attempt Trunk A, failover to Trunk B)
- **FR-019**: System MUST normalize outbound numbers according to policy rules (strip/prepend digits)
- **FR-020**: System MUST block outbound calls that don't match any policy rule with user-facing error message
- **FR-021**: System MUST support both registration-based and IP-authenticated trunks
- **FR-022**: System MUST allow trunks to be tenant-specific or global (shared across tenants)

#### Apply & Configuration Management

- **FR-023**: System MUST use PostgreSQL advisory locks to serialize apply operations (prevent concurrent applies)
- **FR-024**: System MUST generate Asterisk configuration files in isolated staging directory before applying
- **FR-025**: System MUST validate all pending changes for conflicts (duplicate extensions, invalid DIDs, missing references) before generating configs
- **FR-026**: System MUST backup current working config files before applying new configs
- **FR-027**: System MUST write new config files atomically (tmp file + rename)
- **FR-028**: System MUST reload Asterisk modules via AMI (preferred) or CLI (fallback)
- **FR-029**: System MUST automatically rollback to previous config if any reload command fails
- **FR-030**: System MUST create ApplyJob audit record with status (PENDING, RUNNING, SUCCESS, FAILED, ROLLED_BACK), timestamps, error details, and actor

#### End User Self-Service

- **FR-031**: System MUST allow end users to toggle Do Not Disturb (routes incoming calls to voicemail when enabled)
- **FR-032**: System MUST allow end users to set call forwarding destination (immediate forward)
- **FR-033**: System MUST allow end users to change voicemail PIN (hashed storage)
- **FR-034**: System MUST allow end users to upload voicemail greeting audio file (validate format: MP3/WAV, max size: 5MB)
- **FR-035**: System MUST apply end-user self-service changes immediately without requiring admin apply operation

#### Tenant Management

- **FR-036**: System MUST support multi-tenant isolation (each tenant has independent users, extensions, DIDs, policies)
- **FR-037**: System MUST enforce extension range boundaries per tenant (ext_min, ext_max, ext_next pointer)
- **FR-038**: System MUST allow platform admin to suspend tenants (blocks all calling for that tenant)
- **FR-039**: System MUST associate each user, device, DID, policy, and audit log entry with a tenant_id

#### Authentication & Authorization (RBAC)

- **FR-040**: System MUST support four roles: Platform Admin (super), Tenant Admin, Support (read-only), End User
- **FR-041**: System MUST enforce role-based access control server-side (all API endpoints check permissions)
- **FR-042**: System MUST reflect user's role in UI (hide/disable actions user cannot perform)
- **FR-043**: System MUST hash user passwords with bcrypt or argon2
- **FR-044**: System MUST require HTTPS for all web traffic (HTTP redirects to HTTPS)

#### Audit & Observability

- **FR-045**: System MUST log every create/update/delete action to AuditLog with: actor_id, action, entity_type, entity_id, before_json, after_json, timestamp, source_ip
- **FR-046**: System MUST retain apply job logs indefinitely (for compliance and troubleshooting)
- **FR-047**: System MUST provide health check endpoint that verifies: database connectivity, AMI connectivity, Asterisk running status, disk space
- **FR-048**: System MUST emit structured logs (JSON format recommended) for all errors and important events

#### Asterisk Integration

- **FR-049**: System MUST connect to Asterisk via AMI for reloads and status queries
- **FR-050**: System MUST generate PJSIP configuration in isolated include files (portal/generated_endpoints.conf, portal/generated_aors.conf, portal/generated_auths.conf)
- **FR-051**: System MUST generate dialplan configuration in isolated include files (portal/generated_inbound.conf, portal/generated_internal.conf, portal/generated_outbound.conf)
- **FR-052**: System MUST NOT modify hand-written Asterisk config files (only manage portal-owned includes)
- **FR-053**: System MUST support AstDB-based DID lookup OR generated dialplan entries (implementation choice)

### Key Entities

- **Tenant**: Represents an organization/company using the PBX. Attributes: name, timezone, extension range (min/max/next), default inbound destination, outbound policy default, status (active/suspended).

- **User**: Represents a person who uses the phone system. Belongs to one tenant. Attributes: username/email, full name, role (admin/support/end-user), status (active/suspended), auto-assigned extension, outbound caller ID, voicemail settings (enabled, PIN hash), self-service preferences (DND, call forwarding). Relationships: has many Devices, has one Extension, can be assigned DIDs.

- **Device**: Represents a physical or soft phone. Belongs to one user. Attributes: label (e.g., "Desk Phone", "Mobile App"), SIP username (often extension-based), encrypted SIP password, transport (UDP/TCP), NAT flags, codec preferences. Relationships: belongs to User, has registration status (queried from Asterisk).

- **Extension**: Auto-assigned phone number within tenant's range. Represented as User.extension field. Attributes: number (integer, e.g., 1000-1999), uniqueness enforced per tenant.

- **DID**: External phone number. Belongs to one tenant. Attributes: did_number (E.164 format), label, optional provider name, destination_type (enum: USER, RING_GROUP, IVR, QUEUE, VOICEMAIL, EXTERNAL), destination_target (e.g., user_id or extension number). Relationships: routed to User, Ring Group, IVR, etc.

- **Trunk**: SIP trunk for outbound/inbound calling. Can be global or tenant-specific. Attributes: name, host/IP, authentication (registration or IP-auth), transport, codec preferences, enabled status. Relationships: used by OutboundPolicy.

- **OutboundPolicy**: Rules for outbound calling. Belongs to one tenant. Attributes: name, rules (dial patterns, transformations, trunk priority list stored as JSON). Relationships: enforced for User calls.

- **ApplyJob**: Represents one configuration apply operation. Attributes: status (enum: PENDING, RUNNING, SUCCESS, FAILED, ROLLED_BACK), started/ended timestamps, error text, diff summary, actor (user who triggered apply). Relationships: belongs to Tenant, created by User (actor).

- **AuditLog**: Immutable log of all system changes. Attributes: actor_id (user who made change), action (create/update/delete), entity_type (User/Device/DID/etc.), entity_id, before_json (state before change), after_json (state after change), timestamp, source_ip. Relationships: belongs to Tenant and User (actor).

## Success Criteria *(mandatory)*

### Measurable Outcomes

#### Provisioning Reliability

- **SC-001**: 100% of user creation operations result in a unique extension assignment (zero duplicate extensions)
- **SC-002**: User creation completes within 10 seconds from form submission to database commit
- **SC-003**: SIP device registration succeeds within 5 seconds of entering credentials (given valid credentials and network connectivity)

#### Inbound Call Routing

- **SC-004**: 100% of inbound calls to assigned DIDs reach the correct destination user/queue/IVR
- **SC-005**: DID lookup decision completes within 50ms (portal-side database lookup) or 5ms (AstDB-based lookup)
- **SC-006**: Calls to unassigned DIDs route to tenant default destination within 2 seconds

#### Configuration Apply Safety

- **SC-007**: Apply operation success rate ≥ 99% (excluding invalid user inputs like duplicate extensions)
- **SC-008**: Zero instances of apply operation leaving Asterisk in non-functional state (all failures result in automatic rollback)
- **SC-009**: Apply operation completes within 30 seconds for configurations with up to 100 users
- **SC-010**: 100% of apply operations create audit log entry with complete before/after state

#### Admin Operational Efficiency

- **SC-011**: Tenant admin can complete end-to-end workflow (create user → assign DID → verify device registration) in under 2 minutes
- **SC-012**: 90% of device registration troubleshooting can be completed using portal diagnostics without accessing Asterisk CLI

#### End User Experience

- **SC-013**: End user self-service changes (DND toggle, call forwarding) take effect within 5 seconds
- **SC-014**: 95% of end users successfully complete self-service tasks (change voicemail PIN, upload greeting) on first attempt without support

#### System Reliability

- **SC-015**: Portal uptime ≥ 99.5% (excluding planned maintenance)
- **SC-016**: System handles 1000 concurrent tenant admin sessions without response time degradation
- **SC-017**: API endpoints respond within 500ms for typical operations (user list, DID list, device status)
- **SC-018**: Health check endpoint responds within 2 seconds and accurately reflects system status

#### Multi-Tenant Scalability

- **SC-019**: System supports at least 100 tenants with complete data isolation (zero cross-tenant data leakage)
- **SC-020**: Tenant A's apply operation does not impact Tenant B's call quality or device registrations

#### Audit & Compliance

- **SC-021**: 100% of privileged actions (user create/delete, DID assignment, policy changes) are logged to audit trail
- **SC-022**: Audit logs include complete before/after state for all changes (enable exact rollback or review)
- **SC-023**: SIP passwords are never visible in logs, audit trails, or API responses (only hashed storage)

#### Outbound Call Control

- **SC-024**: Outbound policy enforcement blocks 100% of unauthorized call patterns (e.g., international calls when policy is "Local Only")
- **SC-025**: Trunk failover completes within 3 seconds when primary trunk is unavailable

#### Observability

- **SC-026**: Admin can identify cause of apply failure within 1 minute by viewing apply job error details
- **SC-027**: Support user can determine device registration status for a user within 10 seconds of viewing diagnostics page
- **SC-028**: System emits structured error logs that enable root cause analysis within 5 minutes of incident
