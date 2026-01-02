# Data Model: PBX Control Portal MVP

**Feature**: PBX Control Portal MVP
**Branch**: 1-pbx-control-portal
**Date**: 2026-01-01

## Overview

Database schema for PBX control portal storing tenants, users, extensions, and audit logs. PostgreSQL at 77.42.28.222. MVP enforces single tenant but schema prepared for multi-tenancy.

---

## Entity Relationship Diagram

```
┌──────────────┐
│   Tenant     │
│              │
│ - id (PK)    │
│ - name       │
│ - created_at │
└──────┬───────┘
       │
       │ 1:N
       │
┌──────▼───────┐       1:1        ┌──────────────┐
│    User      │◄─────────────────┤  Extension   │
│              │                  │              │
│ - id (PK)    │                  │ - id (PK)    │
│ - tenant_id  │                  │ - number     │
│   (FK)       │                  │ - user_id    │
│ - name       │                  │   (FK)       │
│ - email      │                  │ - secret     │
│ - created_at │                  │ - created_at │
└──────────────┘                  └──────────────┘

┌──────────────────────┐
│  ApplyAuditLog       │
│                      │
│ - id (PK)            │
│ - triggered_at       │
│ - triggered_by       │
│ - outcome (enum)     │
│ - error_details      │
│ - files_written      │
│ - reload_results     │
└──────────────────────┘
```

---

## Entities

### Tenant

Represents an organization using the PBX system. MVP uses single default tenant.

**Table**: `tenants`

| Column      | Type         | Constraints           | Description                          |
|-------------|--------------|----------------------|--------------------------------------|
| id          | UUID         | PRIMARY KEY          | Unique tenant identifier             |
| name        | VARCHAR(255) | NOT NULL             | Tenant organization name             |
| created_at  | TIMESTAMP    | NOT NULL, DEFAULT NOW | Tenant creation timestamp            |

**Indexes**:
- PRIMARY KEY on `id`

**Constraints**:
- `name` must not be empty

**Notes**:
- MVP creates single default tenant on first run (name: "Default")
- All users belong to this tenant
- Schema supports multi-tenancy for future expansion

---

### User

Represents a person who can use the PBX.

**Table**: `users`

| Column      | Type         | Constraints              | Description                          |
|-------------|--------------|--------------------------|--------------------------------------|
| id          | UUID         | PRIMARY KEY              | Unique user identifier               |
| tenant_id   | UUID         | NOT NULL, FOREIGN KEY    | Reference to tenants.id              |
| name        | VARCHAR(255) | NOT NULL                 | User full name                       |
| email       | VARCHAR(255) | NOT NULL, UNIQUE         | User email address                   |
| created_at  | TIMESTAMP    | NOT NULL, DEFAULT NOW    | User creation timestamp              |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `email` (prevents duplicate users)
- INDEX on `tenant_id` (foreign key lookup)

**Constraints**:
- `tenant_id` FOREIGN KEY REFERENCES `tenants(id)` ON DELETE CASCADE
- `name` must not be empty
- `email` must be valid format (application-level validation)

**Relationships**:
- Many-to-one with Tenant (user.tenant_id → tenant.id)
- One-to-one with Extension (user.id ← extension.user_id)

---

### Extension

Represents a SIP extension number allocated to a user.

**Table**: `extensions`

| Column      | Type         | Constraints              | Description                          |
|-------------|--------------|--------------------------|--------------------------------------|
| id          | UUID         | PRIMARY KEY              | Unique extension identifier          |
| number      | INTEGER      | NOT NULL, UNIQUE, CHECK  | Extension number (1000-1999)         |
| user_id     | UUID         | NOT NULL, UNIQUE, FK     | Reference to users.id                |
| secret      | VARCHAR(255) | NOT NULL                 | SIP authentication password          |
| created_at  | TIMESTAMP    | NOT NULL, DEFAULT NOW    | Extension allocation timestamp       |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE on `number` (prevents duplicate extension numbers)
- UNIQUE on `user_id` (enforces one extension per user)
- INDEX on `number` (range queries for allocation)

**Constraints**:
- `number` CHECK (number >= 1000 AND number <= 1999)
- `user_id` FOREIGN KEY REFERENCES `users(id)` ON DELETE CASCADE
- `secret` must not be empty

**Relationships**:
- One-to-one with User (extension.user_id → user.id)

**Allocation Logic** (concurrency-safe):
```sql
-- Find lowest available extension
SELECT MIN(candidate)
FROM generate_series(1000, 1999) AS candidate
WHERE candidate NOT IN (SELECT number FROM extensions);
```

**Concurrency Safety**:
- UNIQUE constraint on `number` prevents duplicate allocations
- Allocation happens inside DB transaction with retry logic
- If two users created simultaneously, one succeeds, other retries with next available
- Max 5 retries before returning error (handles high concurrency edge cases)

**Secret Generation**:
- Generated using `secrets.token_urlsafe(16)` on extension creation
- Cryptographically secure random string
- Stored plaintext (used in PJSIP auth config)

---

### ApplyAuditLog

Records each Apply action for troubleshooting and compliance.

**Table**: `apply_audit_logs`

| Column          | Type         | Constraints              | Description                          |
|-----------------|--------------|--------------------------|--------------------------------------|
| id              | UUID         | PRIMARY KEY              | Unique log entry identifier          |
| triggered_at    | TIMESTAMP    | NOT NULL, DEFAULT NOW    | When apply was triggered             |
| triggered_by    | VARCHAR(255) | NOT NULL                 | Admin user who triggered apply       |
| outcome         | VARCHAR(50)  | NOT NULL, CHECK          | 'success' or 'failure'               |
| error_details   | TEXT         | NULL                     | Error message if outcome=failure     |
| files_written   | TEXT[]       | NULL                     | Array of file paths written          |
| reload_results  | JSONB        | NULL                     | Asterisk reload command results      |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `triggered_at` DESC (recent logs lookup)

**Constraints**:
- `outcome` CHECK (outcome IN ('success', 'failure'))
- `error_details` must be NULL if outcome='success'

**JSONB reload_results structure**:
```json
{
  "pjsip_reload": {
    "command": "asterisk -rx 'pjsip reload'",
    "exit_code": 0,
    "stdout": "...",
    "stderr": ""
  },
  "dialplan_reload": {
    "command": "asterisk -rx 'dialplan reload'",
    "exit_code": 0,
    "stdout": "...",
    "stderr": ""
  }
}
```

---

## Database Migrations

**Tool**: Alembic (SQLAlchemy migration framework)

**Migration Structure**:
```
migrations/
├── versions/
│   ├── 001_initial_schema.py      # Create tenants, users, extensions, audit_logs
│   └── 002_default_tenant.py      # Insert default tenant (data migration)
└── env.py                         # Alembic configuration
```

**Initial Migration** (001_initial_schema.py):
1. Create `tenants` table
2. Create `users` table with tenant FK
3. Create `extensions` table with user FK and number constraint
4. Create `apply_audit_logs` table
5. Create all indexes

**Default Tenant Migration** (002_default_tenant.py):
```python
def upgrade():
    op.execute("""
        INSERT INTO tenants (id, name, created_at)
        VALUES (
            'a0000000-0000-0000-0000-000000000000',
            'Default',
            NOW()
        )
    """)
```

---

## Data Validation Rules

### User Creation
- `name`: Required, non-empty, max 255 chars
- `email`: Required, valid email format (regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
- `tenant_id`: Must reference existing tenant (default tenant ID)

### Extension Allocation
- Automatic on user creation
- Algorithm: Find MIN(number) WHERE number NOT IN (allocated) AND number BETWEEN 1000 AND 1999
- If no available extension (all 1000 allocated), reject user creation with error
- Transaction isolation: Use SERIALIZABLE to prevent race conditions

### Apply Audit Logging
- `triggered_by`: Required, non-empty (admin identifier)
- `outcome`: Must be 'success' or 'failure'
- `error_details`: Required if outcome='failure', NULL otherwise
- `files_written`: Array of absolute paths to generated config files
- `reload_results`: JSONB with command outputs (nullable if write fails before reload)

---

## State Transitions

### User Lifecycle
```
[Not Exists] --POST /users--> [Created + Extension Allocated]
                                        |
                                        | (DB only, not in Asterisk yet)
                                        |
                                POST /apply
                                        |
                                        v
                              [In Asterisk Config]
                                        |
                                        | (User can register SIP extension)
                                        |
                              DELETE /users/{id}
                                        |
                                        v
                              [Deleted from DB]
                                        |
                                        | (Still in Asterisk until next Apply)
                                        |
                                POST /apply
                                        |
                                        v
                              [Removed from Asterisk]
```

### Extension Lifecycle
```
[Available in Pool 1000-1999]
            |
            | User creation
            |
            v
[Allocated to User]
            |
            | User deletion
            |
            v
[Freed, back to pool]
```

### Apply Operation State
```
[Idle] --POST /apply--> [Lock Acquired]
                              |
                              | Generate configs
                              |
                              v
                        [Writing Files]
                              |
                              | Atomic write (temp → rename)
                              |
                              v
                        [Reloading Asterisk]
                              |
                              | SSH: asterisk -rx "pjsip reload"
                              | SSH: asterisk -rx "dialplan reload"
                              |
                              v
                        [Logging Audit]
                              |
                              | Insert apply_audit_log
                              |
                              v
                        [Lock Released] --> [Idle]
```

---

## Performance Considerations

### Extension Allocation Query Optimization
- Index on `extensions.number` enables fast MIN lookup
- Generate_series(1000, 1999) creates 1000-row set (small, fast)
- Worst case (999 allocated): Still <1ms query time on modern PostgreSQL
- **Concurrency**: UNIQUE constraint + retry pattern handles simultaneous allocations without SELECT FOR UPDATE lock contention

### Apply Operation Concurrency
- PostgreSQL advisory lock (pg_advisory_lock) prevents concurrent applies
- Lock acquired before config generation, released after audit log
- If second apply starts during first, blocks until first completes (or use pg_try_advisory_lock for fail-fast)

### Audit Log Growth
- INDEX on `triggered_at DESC` for efficient recent log queries
- No automatic cleanup in MVP (manual maintenance if needed)
- Future: Partition by month or auto-archive old logs

---

## Schema SQL (Reference)

```sql
-- Tenants
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL CHECK (name <> ''),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL CHECK (name <> ''),
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);

-- Extensions
CREATE TABLE extensions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    number INTEGER NOT NULL UNIQUE CHECK (number >= 1000 AND number <= 1999),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    secret VARCHAR(255) NOT NULL CHECK (secret <> ''),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_extensions_number ON extensions(number);

-- Apply Audit Logs
CREATE TABLE apply_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    triggered_by VARCHAR(255) NOT NULL CHECK (triggered_by <> ''),
    outcome VARCHAR(50) NOT NULL CHECK (outcome IN ('success', 'failure')),
    error_details TEXT,
    files_written TEXT[],
    reload_results JSONB
);
CREATE INDEX idx_apply_audit_logs_triggered_at ON apply_audit_logs(triggered_at DESC);

-- Default Tenant (data migration)
INSERT INTO tenants (id, name) VALUES
    ('a0000000-0000-0000-0000-000000000000', 'Default');
```

---

## Summary

4 entities: Tenant (single default), User (admin-created), Extension (auto-allocated 1000-1999), ApplyAuditLog (apply tracking).

Key features:
- Extension allocation via SQL MIN query (handles gaps from deletes)
- SIP secrets generated securely (secrets.token_urlsafe)
- Apply serialization via PostgreSQL advisory locks
- Audit logging for compliance and troubleshooting
- Schema supports future multi-tenancy (MVP enforces single tenant)

Ready for contract definition (API endpoints using these entities).
