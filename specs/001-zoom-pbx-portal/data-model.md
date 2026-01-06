# Data Model: Zoom-Style PBX Management Portal

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-01-05

## Overview

This document defines the complete data model for the Zoom-style PBX management portal. Entities are stored in PostgreSQL (application data) and MariaDB (Asterisk PJSIP Realtime). The model supports multi-tenant isolation, RBAC, DID routing, device management, outbound policies, and complete audit trails.

**Storage Strategy**:
- **PostgreSQL**: All application data (tenants, users, devices, DIDs, policies, audit logs)
- **MariaDB**: Asterisk PJSIP Realtime only (ps_endpoints, ps_auths, ps_aors)
- **File System**: Generated Asterisk dialplan configurations (inbound/internal/outbound routing)

---

## Core Entities

### 1. Tenant

**Purpose**: Represents an organization/company using the PBX system. Complete isolation boundary.

**Table**: `tenants`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique tenant identifier |
| `name` | VARCHAR(255) | NOT NULL | Organization name (display) |
| `timezone` | VARCHAR(50) | NOT NULL, DEFAULT 'UTC' | IANA timezone (e.g., "America/New_York") |
| `ext_min` | INTEGER | NOT NULL | Extension range minimum (e.g., 1000) |
| `ext_max` | INTEGER | NOT NULL | Extension range maximum (e.g., 1999) |
| `ext_next` | INTEGER | NOT NULL | Next available extension (auto-increment pointer) |
| `default_inbound_destination` | VARCHAR(255) | NULLABLE | Default destination for unassigned DIDs (e.g., "IVR:main", "VOICEMAIL:general") |
| `outbound_policy_id` | UUID | FK → `outbound_policies.id`, NULLABLE | Default outbound calling policy |
| `status` | ENUM | NOT NULL, DEFAULT 'active' | Values: `active`, `suspended` |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Relationships**:
- **Has Many**: Users, Devices, DIDs, OutboundPolicies, ApplyJobs, AuditLogs
- **Belongs To**: OutboundPolicy (default policy)

**Validation Rules**:
- `ext_min` < `ext_max` (range must be valid)
- `ext_next` must be between `ext_min` and `ext_max` (enforced at user creation)
- Extension range must accommodate at least 10 extensions (ext_max - ext_min >= 10)
- `name` must be unique across all tenants

**State Transitions**:
```
active → suspended: Platform Admin suspends tenant (blocks all calling)
suspended → active: Platform Admin restores tenant
```

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `name`
- INDEX on `status` (for filtering active tenants)

---

### 2. User

**Purpose**: Represents a person who uses the phone system. Core entity for provisioning.

**Table**: `users`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique user identifier |
| `tenant_id` | UUID | FK → `tenants.id`, NOT NULL, ON DELETE CASCADE | Parent tenant |
| `username` | VARCHAR(255) | NOT NULL | Login username (email format recommended) |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | User email address |
| `password_hash` | TEXT | NOT NULL | Argon2/bcrypt hash of login password |
| `full_name` | VARCHAR(255) | NOT NULL | Display name (e.g., "John Doe") |
| `role` | ENUM | NOT NULL, DEFAULT 'end_user' | Values: `platform_admin`, `tenant_admin`, `support`, `end_user` |
| `status` | ENUM | NOT NULL, DEFAULT 'active' | Values: `active`, `suspended`, `deleted` (soft delete) |
| `extension` | INTEGER | UNIQUE (per tenant), NOT NULL | Auto-assigned extension number |
| `outbound_callerid` | VARCHAR(20) | NULLABLE | Custom caller ID for outbound calls (E.164 format) |
| `voicemail_enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Enable voicemail box |
| `voicemail_pin_hash` | TEXT | NULLABLE | Hashed voicemail PIN (bcrypt) |
| `dnd_enabled` | BOOLEAN | NOT NULL, DEFAULT FALSE | Do Not Disturb (routes to voicemail) |
| `call_forward_destination` | VARCHAR(255) | NULLABLE | Immediate forward destination (extension or E.164 number) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Relationships**:
- **Belongs To**: Tenant
- **Has Many**: Devices
- **Referenced By**: DIDs (as destination), AuditLogs (as actor)

**Validation Rules**:
- `email` must be valid email format (RFC 5322)
- `extension` must be within tenant's `ext_min` and `ext_max` range
- `extension` must be unique within tenant (enforced by composite unique constraint)
- `outbound_callerid` must be E.164 format if provided (e.g., "+15551234567")
- `call_forward_destination` must be valid extension or E.164 number if provided
- `role` = `platform_admin` can only be assigned by existing platform_admin

**State Transitions**:
```
active → suspended: Tenant Admin or Platform Admin suspends user (blocks login and calling)
active → deleted: Soft delete (preserves audit trail, blocks login/calling)
suspended → active: Restore user
deleted → (no transition): Permanent state
```

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `email`
- UNIQUE on (`tenant_id`, `extension`)
- INDEX on `tenant_id` (for tenant queries)
- INDEX on `status` (for filtering active users)

---

### 3. Device

**Purpose**: Represents a physical or soft phone registered to a user. Enables multi-device support.

**Table**: `devices`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique device identifier |
| `user_id` | UUID | FK → `users.id`, NOT NULL, ON DELETE CASCADE | Parent user |
| `tenant_id` | UUID | FK → `tenants.id`, NOT NULL, ON DELETE CASCADE | Parent tenant (denormalized for queries) |
| `label` | VARCHAR(255) | NOT NULL | User-facing label (e.g., "Desk Phone", "Mobile App") |
| `sip_username` | VARCHAR(255) | NOT NULL, UNIQUE | Unique SIP username (e.g., "1001-desk", "1001-mobile") |
| `sip_password_encrypted` | TEXT | NOT NULL | Fernet-encrypted SIP password (reversible encryption) |
| `transport` | ENUM | NOT NULL, DEFAULT 'udp' | Values: `udp`, `tcp`, `tls`, `wss` |
| `nat_flags_json` | JSONB | NULLABLE | NAT traversal flags (e.g., `{"force_rport": true, "comedia": true}`) |
| `codecs_json` | JSONB | NOT NULL, DEFAULT '["ulaw", "alaw"]' | Codec preference list (ordered array) |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Enable/disable device without deleting |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Relationships**:
- **Belongs To**: User, Tenant

**Validation Rules**:
- `sip_username` must be unique across all tenants (global uniqueness)
- `sip_username` format: `{extension}-{device-slug}` (e.g., "1001-desk", "1001-mobile")
- `sip_password_encrypted` must be Fernet-encrypted ciphertext (decrypt for MariaDB sync)
- `codecs_json` must be valid JSON array of codec names (e.g., `["ulaw", "alaw", "g722"]`)
- `label` must be unique per user (e.g., user can't have two "Desk Phone" devices)

**State Transitions**:
```
enabled=true → enabled=false: Disable device (blocks SIP registration, keeps config)
enabled=false → enabled=true: Re-enable device
(any state) → DELETED: Hard delete (cascade from user deletion)
```

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `sip_username`
- INDEX on `user_id` (for user's devices query)
- INDEX on `tenant_id` (for tenant's devices query)
- INDEX on `enabled` (for filtering active devices)

**MariaDB Sync**: Each device creates entries in MariaDB:
- `ps_endpoints`: SIP endpoint configuration (context, codecs, transport, callerid)
- `ps_auths`: Authentication credentials (username, password, auth_type=userpass)
- `ps_aors`: Address of Record (shared AOR for all user's devices, max_contacts=10)

---

### 4. Extension

**Purpose**: Auto-assigned phone number within tenant's range. Represented as `User.extension` field.

**Implementation**: NOT a separate table. Extension is a column on the `users` table with composite uniqueness constraint.

**Attributes**: See `User.extension` field.

**Allocation Algorithm**:
```python
def allocate_extension(tenant_id: UUID) -> int:
    """
    Allocate next available extension for tenant.
    Uses tenant.ext_next pointer for O(1) allocation.
    """
    tenant = session.query(Tenant).filter(Tenant.id == tenant_id).with_for_update().one()

    if tenant.ext_next > tenant.ext_max:
        raise ExtensionPoolExhausted(f"Tenant {tenant.name} has no available extensions")

    extension = tenant.ext_next
    tenant.ext_next += 1
    session.commit()

    return extension
```

**Validation Rules**:
- Extension must be within tenant's `ext_min` and `ext_max` range
- Extension must be unique per tenant (enforced by database constraint)
- Cannot manually assign extension (always use auto-allocator)

---

### 5. DID (Direct Inward Dialing)

**Purpose**: External phone number that routes inbound calls to destinations.

**Table**: `dids`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique DID identifier |
| `tenant_id` | UUID | FK → `tenants.id`, NOT NULL, ON DELETE CASCADE | Parent tenant |
| `did_number` | VARCHAR(20) | NOT NULL, UNIQUE | E.164 formatted phone number (e.g., "+15551234567") |
| `label` | VARCHAR(255) | NULLABLE | User-facing label (e.g., "Main Office Line", "Sales Hotline") |
| `provider` | VARCHAR(255) | NULLABLE | SIP trunk provider name (e.g., "Twilio", "Bandwidth") |
| `destination_type` | ENUM | NOT NULL | Values: `USER`, `RING_GROUP`, `IVR`, `QUEUE`, `VOICEMAIL`, `EXTERNAL` |
| `destination_target` | VARCHAR(255) | NOT NULL | Destination identifier (user_id UUID, extension number, or external number) |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Enable/disable DID without deleting |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Relationships**:
- **Belongs To**: Tenant
- **References**: User (when destination_type = USER)

**Validation Rules**:
- `did_number` must be E.164 format: `+[1-9]\d{1,14}` (e.g., "+15551234567")
- `did_number` must be unique across all tenants (global uniqueness)
- `destination_target` validation depends on `destination_type`:
  - `USER`: Must be valid `users.id` UUID within same tenant
  - `RING_GROUP`: Must be valid ring group ID (future feature)
  - `IVR`: Must be valid IVR ID (future feature)
  - `QUEUE`: Must be valid queue ID (future feature)
  - `VOICEMAIL`: Must be valid extension number or "general"
  - `EXTERNAL`: Must be E.164 formatted number

**State Transitions**:
```
enabled=true → enabled=false: Disable DID (routes to tenant default destination)
enabled=false → enabled=true: Re-enable DID
```

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `did_number`
- INDEX on `tenant_id` (for tenant's DIDs query)
- INDEX on (`destination_type`, `destination_target`) (for reverse lookup: "which DIDs point to user X?")

**Dialplan Generation**: Each DID creates an entry in `generated_inbound.conf`:
```asterisk
; DID +15551234567 → User 1001
exten => +15551234567,1,NoOp(Inbound DID: ${EXTEN})
 same => n,Set(CALLERID(name)=Inbound Call)
 same => n,Dial(PJSIP/1001,30)
 same => n,Voicemail(1001,u)
 same => n,Hangup()
```

---

### 6. Trunk

**Purpose**: SIP trunk for outbound/inbound calling. Connects to external providers.

**Table**: `trunks`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique trunk identifier |
| `tenant_id` | UUID | FK → `tenants.id`, NULLABLE, ON DELETE CASCADE | Parent tenant (NULL = global trunk) |
| `name` | VARCHAR(255) | NOT NULL | Trunk name (e.g., "Twilio Main", "Bandwidth Emergency") |
| `host` | VARCHAR(255) | NOT NULL | SIP server hostname or IP (e.g., "sip.twilio.com") |
| `auth_mode` | ENUM | NOT NULL | Values: `registration`, `ip_auth` |
| `registration_string` | TEXT | NULLABLE | SIP REGISTER string (required if auth_mode=registration) |
| `transport` | ENUM | NOT NULL, DEFAULT 'udp' | Values: `udp`, `tcp`, `tls` |
| `codecs_json` | JSONB | NOT NULL, DEFAULT '["ulaw", "alaw"]' | Codec preference list |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Enable/disable trunk |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Relationships**:
- **Belongs To**: Tenant (or NULL for global trunks)
- **Referenced By**: OutboundPolicy (trunk priority list)

**Validation Rules**:
- `name` must be unique within tenant (or unique among global trunks if tenant_id=NULL)
- `host` must be valid hostname or IP address
- If `auth_mode` = `registration`, `registration_string` is required
- If `auth_mode` = `ip_auth`, `registration_string` must be NULL
- `codecs_json` must be valid JSON array of codec names

**State Transitions**:
```
enabled=true → enabled=false: Disable trunk (outbound policies using this trunk will fail over to next trunk in priority list)
enabled=false → enabled=true: Re-enable trunk
```

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `tenant_id` (for tenant's trunks query, includes NULL for global trunks)
- INDEX on `enabled` (for filtering active trunks)

---

### 7. OutboundPolicy

**Purpose**: Rules for outbound calling. Controls which numbers users can dial and which trunks to use.

**Table**: `outbound_policies`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique policy identifier |
| `tenant_id` | UUID | FK → `tenants.id`, NOT NULL, ON DELETE CASCADE | Parent tenant |
| `name` | VARCHAR(255) | NOT NULL | Policy name (e.g., "Local Only", "International", "Emergency") |
| `rules_json` | JSONB | NOT NULL | Policy rules (patterns, transformations, trunk priority) - see schema below |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Enable/disable policy |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Relationships**:
- **Belongs To**: Tenant
- **Referenced By**: Tenant (default_outbound_policy_id), User (future: per-user policy override)
- **References**: Trunks (via `rules_json.trunk_priority` array)

**`rules_json` Schema**:
```json
{
  "rules": [
    {
      "pattern": "^1[2-9]\\d{9}$",
      "description": "North American 11-digit numbers",
      "transformations": [
        {"type": "prepend", "value": "1"},
        {"type": "strip", "count": 1}
      ],
      "trunk_priority": ["trunk-uuid-1", "trunk-uuid-2"]
    },
    {
      "pattern": "^011\\d{7,15}$",
      "description": "International calls",
      "transformations": [],
      "trunk_priority": ["trunk-uuid-3"]
    }
  ],
  "default_action": "block"
}
```

**Validation Rules**:
- `name` must be unique within tenant
- `rules_json` must be valid JSON matching the schema above
- Each rule's `pattern` must be valid regex
- Each trunk UUID in `trunk_priority` must reference existing enabled trunk
- `default_action` must be one of: `block`, `allow_with_warning`

**State Transitions**:
```
enabled=true → enabled=false: Disable policy (users revert to tenant default policy)
enabled=false → enabled=true: Re-enable policy
```

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `tenant_id` (for tenant's policies query)
- INDEX on `enabled` (for filtering active policies)

**Dialplan Generation**: Each policy creates pattern matching logic in `generated_outbound.conf`:
```asterisk
; Policy: Local Only
exten => _NXXNXXXXXX,1,NoOp(Outbound call via Local Only policy)
 same => n,Set(CHANNEL(language)=en)
 same => n,Dial(PJSIP/${EXTEN}@trunk-1,30)
 same => n,GotoIf($["${DIALSTATUS}" = "CHANUNAVAIL"]?failover)
 same => n,Hangup()
 same => n(failover),Dial(PJSIP/${EXTEN}@trunk-2,30)
 same => n,Hangup()

; Block all other patterns (no match)
exten => _X.,1,NoOp(Blocked by policy: ${EXTEN})
 same => n,Playback(ss-noservice)
 same => n,Hangup()
```

---

### 8. ApplyJob

**Purpose**: Represents one configuration apply operation. Provides audit trail and rollback capability.

**Table**: `apply_jobs`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique apply job identifier |
| `tenant_id` | UUID | FK → `tenants.id`, NULLABLE | Tenant whose config is being applied (NULL = system-wide apply) |
| `actor_id` | UUID | FK → `users.id`, NOT NULL | User who triggered the apply |
| `status` | ENUM | NOT NULL, DEFAULT 'PENDING' | Values: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `ROLLED_BACK` |
| `started_at` | TIMESTAMP | NULLABLE | When apply started |
| `ended_at` | TIMESTAMP | NULLABLE | When apply completed (success or failure) |
| `error_text` | TEXT | NULLABLE | Error message if status=FAILED |
| `diff_summary` | TEXT | NULLABLE | Summary of changes (e.g., "Added 3 users, updated 2 DIDs") |
| `config_files_json` | JSONB | NULLABLE | List of config files written (for rollback) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Job creation timestamp |

**Relationships**:
- **Belongs To**: Tenant (optional), User (actor)

**Validation Rules**:
- `started_at` must be >= `created_at`
- `ended_at` must be >= `started_at` (if set)
- `error_text` required if `status` = `FAILED` or `ROLLED_BACK`
- Only one apply job per tenant can be in `RUNNING` status at a time (enforced by PostgreSQL advisory lock)

**State Transitions**:
```
PENDING → RUNNING: Apply starts (acquire advisory lock)
RUNNING → SUCCESS: Apply completes successfully (release lock)
RUNNING → FAILED: Apply fails, rollback not attempted (release lock)
RUNNING → ROLLED_BACK: Apply fails, rollback executed (release lock)
```

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `tenant_id` (for tenant's apply history)
- INDEX on `actor_id` (for user's apply history)
- INDEX on `status` (for querying active/failed applies)
- INDEX on `created_at` (for chronological queries)

---

### 9. AuditLog

**Purpose**: Immutable log of all system changes. Enables compliance, troubleshooting, and rollback.

**Table**: `audit_logs`

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique audit log entry identifier |
| `tenant_id` | UUID | FK → `tenants.id`, NULLABLE | Tenant context (NULL for platform-level actions) |
| `actor_id` | UUID | FK → `users.id`, NOT NULL | User who performed the action |
| `action` | ENUM | NOT NULL | Values: `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, `APPLY` |
| `entity_type` | VARCHAR(50) | NOT NULL | Entity type (e.g., "User", "Device", "DID", "Trunk") |
| `entity_id` | UUID | NOT NULL | ID of the entity that was modified |
| `before_json` | JSONB | NULLABLE | Entity state before change (NULL for CREATE) |
| `after_json` | JSONB | NULLABLE | Entity state after change (NULL for DELETE) |
| `timestamp` | TIMESTAMP | NOT NULL, DEFAULT NOW() | When action occurred |
| `source_ip` | VARCHAR(45) | NULLABLE | Source IP address (IPv4 or IPv6) |
| `user_agent` | TEXT | NULLABLE | User agent string (for web requests) |

**Relationships**:
- **Belongs To**: Tenant (optional), User (actor)

**Validation Rules**:
- `before_json` must be NULL if `action` = `CREATE`
- `after_json` must be NULL if `action` = `DELETE`
- Both `before_json` and `after_json` must be non-NULL if `action` = `UPDATE`
- `entity_type` must be one of: User, Device, DID, Trunk, OutboundPolicy, Tenant, ApplyJob
- Audit log entries are immutable (no UPDATE or DELETE operations allowed)

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `tenant_id` (for tenant's audit trail)
- INDEX on `actor_id` (for user's action history)
- INDEX on (`entity_type`, `entity_id`) (for entity's change history)
- INDEX on `timestamp` (for chronological queries)
- INDEX on `action` (for filtering by action type)

**Retention Policy**: Retain indefinitely (compliance requirement FR-046).

---

## Relationships Diagram

```
┌──────────────┐
│   Tenant     │
└──────┬───────┘
       │
       │ 1:N
       ├─────────────────────────────────────┐
       │                                     │
       ▼                                     ▼
┌──────────────┐                      ┌──────────────┐
│     User     │                      │     DID      │
└──────┬───────┘                      └──────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐
│    Device    │
└──────────────┘

       │
       │ (Tenant also has)
       ├─────────────────────────────────────┬────────────────────┐
       │                                     │                    │
       ▼                                     ▼                    ▼
┌──────────────┐                      ┌──────────────┐    ┌──────────────┐
│    Trunk     │                      │OutboundPolicy│    │  ApplyJob    │
└──────────────┘                      └──────────────┘    └──────────────┘

       │
       │ (All entities have)
       ▼
┌──────────────┐
│  AuditLog    │
└──────────────┘
```

**Key Relationships**:
- Tenant → Users (1:N, cascade delete)
- Tenant → Devices (1:N, cascade delete)
- Tenant → DIDs (1:N, cascade delete)
- Tenant → Trunks (1:N, cascade delete, NULL tenant_id = global trunk)
- Tenant → OutboundPolicies (1:N, cascade delete)
- Tenant → ApplyJobs (1:N, no cascade)
- Tenant → AuditLogs (1:N, no cascade)
- User → Devices (1:N, cascade delete)
- User → Extension (1:1, embedded as User.extension field)
- DID → User (N:1, FK on destination_target when destination_type=USER)
- OutboundPolicy → Trunks (N:N via rules_json.trunk_priority array)

---

## Database Constraints

### Foreign Key Constraints

```sql
-- Tenant relationships
ALTER TABLE users ADD CONSTRAINT fk_users_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE devices ADD CONSTRAINT fk_devices_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE devices ADD CONSTRAINT fk_devices_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE dids ADD CONSTRAINT fk_dids_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE trunks ADD CONSTRAINT fk_trunks_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE outbound_policies ADD CONSTRAINT fk_policies_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE apply_jobs ADD CONSTRAINT fk_apply_jobs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL;
ALTER TABLE apply_jobs ADD CONSTRAINT fk_apply_jobs_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL;
ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL;
```

### Unique Constraints

```sql
-- Tenant
ALTER TABLE tenants ADD CONSTRAINT uq_tenants_name UNIQUE (name);

-- User
ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);
ALTER TABLE users ADD CONSTRAINT uq_users_tenant_extension UNIQUE (tenant_id, extension);

-- Device
ALTER TABLE devices ADD CONSTRAINT uq_devices_sip_username UNIQUE (sip_username);
ALTER TABLE devices ADD CONSTRAINT uq_devices_user_label UNIQUE (user_id, label);

-- DID
ALTER TABLE dids ADD CONSTRAINT uq_dids_number UNIQUE (did_number);

-- Trunk
ALTER TABLE trunks ADD CONSTRAINT uq_trunks_tenant_name UNIQUE (tenant_id, name);

-- OutboundPolicy
ALTER TABLE outbound_policies ADD CONSTRAINT uq_policies_tenant_name UNIQUE (tenant_id, name);
```

### Check Constraints

```sql
-- Tenant: Extension range validation
ALTER TABLE tenants ADD CONSTRAINT chk_tenant_ext_range CHECK (ext_min < ext_max);
ALTER TABLE tenants ADD CONSTRAINT chk_tenant_ext_next CHECK (ext_next >= ext_min AND ext_next <= ext_max + 1);

-- User: Extension within tenant range (enforced by trigger, not check constraint)
CREATE OR REPLACE FUNCTION validate_user_extension() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM tenants
        WHERE id = NEW.tenant_id
        AND NEW.extension BETWEEN ext_min AND ext_max
    ) THEN
        RAISE EXCEPTION 'Extension % is outside tenant range', NEW.extension;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_user_extension
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION validate_user_extension();

-- DID: E.164 format validation
ALTER TABLE dids ADD CONSTRAINT chk_did_e164_format CHECK (did_number ~ '^\+[1-9]\d{1,14}$');

-- User: Email format validation (basic)
ALTER TABLE users ADD CONSTRAINT chk_user_email_format CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$');
```

---

## Encryption and Security

### Password Hashing

**User Login Passwords** (`users.password_hash`):
- **Algorithm**: Argon2id (preferred) or bcrypt
- **Storage**: One-way hash (irreversible)
- **Verification**: Compare hash on login

**Voicemail PINs** (`users.voicemail_pin_hash`):
- **Algorithm**: bcrypt
- **Storage**: One-way hash
- **Verification**: Compare hash when accessing voicemail

### SIP Password Encryption

**Device SIP Passwords** (`devices.sip_password_encrypted`):
- **Algorithm**: Fernet symmetric encryption (AES-128 in CBC mode)
- **Storage**: Encrypted ciphertext
- **Key Management**: `FERNET_KEY` environment variable (32 bytes base64-encoded)
- **Decryption**: Required when syncing to MariaDB PJSIP Realtime (plaintext in ps_auths table)

**CRITICAL**: SIP passwords must NEVER appear in:
- API responses (return masked value like "********")
- Audit logs (exclude from `before_json` and `after_json`)
- Application logs

---

## Performance Considerations

### Indexing Strategy

**High-Frequency Queries**:
- User lookup by tenant_id (tenant's user list): INDEX on `users.tenant_id`
- Device lookup by user_id (user's devices): INDEX on `devices.user_id`
- DID lookup by number (inbound call routing): UNIQUE INDEX on `dids.did_number`
- Audit log by entity (entity change history): INDEX on (`audit_logs.entity_type`, `audit_logs.entity_id`)

**Query Patterns**:
```sql
-- Tenant's active users (API endpoint: GET /tenants/{id}/users)
SELECT * FROM users WHERE tenant_id = ? AND status = 'active';
-- Optimized by: INDEX(tenant_id), INDEX(status)

-- User's devices (API endpoint: GET /users/{id}/devices)
SELECT * FROM devices WHERE user_id = ? AND enabled = true;
-- Optimized by: INDEX(user_id), INDEX(enabled)

-- DID reverse lookup (API endpoint: GET /users/{id}/dids)
SELECT * FROM dids WHERE destination_type = 'USER' AND destination_target = ?::text;
-- Optimized by: INDEX(destination_type, destination_target)

-- Recent audit trail (API endpoint: GET /audit-logs?since=...)
SELECT * FROM audit_logs WHERE tenant_id = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT 100;
-- Optimized by: INDEX(tenant_id), INDEX(timestamp)
```

### Pagination

All list endpoints MUST support pagination:
```sql
-- Offset-based pagination (for small datasets)
SELECT * FROM users WHERE tenant_id = ? LIMIT 50 OFFSET 100;

-- Cursor-based pagination (for large datasets, more efficient)
SELECT * FROM users WHERE tenant_id = ? AND id > ? ORDER BY id LIMIT 50;
```

### Denormalization

**`devices.tenant_id`**: Denormalized from `devices.user_id → users.tenant_id`
- **Reason**: Enables direct tenant-scoped device queries without join
- **Trade-off**: Slight write overhead (must update both user_id and tenant_id)
- **Consistency**: Enforced by database trigger

---

## Migration Strategy

### Alembic Migrations

**Migration Order** (from plan.md):
1. `001_initial.py` — ✅ Already exists (tenants, users, extensions)
2. `002_add_devices.py` — Create devices table
3. `003_add_dids.py` — Create dids table
4. `004_add_trunks_policies.py` — Create trunks and outbound_policies tables
5. `005_add_self_service.py` — Extend users table with DND, call forwarding, voicemail fields
6. `006_add_audit_log.py` — Create audit_logs table
7. `007_extend_tenant_user.py` — Extend tenants and users tables with status, roles, etc.

**Migration Testing**:
- Each migration MUST include `upgrade()` and `downgrade()` functions
- Test both upgrade and downgrade paths in development
- Verify foreign key constraints, indexes, and triggers are created

---

## Summary

This data model provides:
- **Multi-tenant isolation**: Complete separation via tenant_id foreign keys
- **RBAC support**: User roles (platform_admin, tenant_admin, support, end_user)
- **Extensibility**: JSONB fields for flexible configuration (nat_flags_json, codecs_json, rules_json)
- **Audit trail**: Complete change tracking in audit_logs table
- **Safety**: Cascade deletes, check constraints, validation triggers
- **Performance**: Strategic indexing for common query patterns

**Next Steps**:
- Generate API contracts (OpenAPI 3.0 spec) from functional requirements → `contracts/openapi.yaml`
- Create developer quickstart guide → `quickstart.md`
- Update agent context → run `update-agent-context.ps1`
