# Research: PBX Control Portal MVP Technology Decisions

**Feature**: PBX Control Portal MVP
**Branch**: 1-pbx-control-portal
**Date**: 2026-01-01

## Overview

This document records technology choices, rationale, and alternatives considered for implementing the PBX control portal backend.

---

## Decision 1: Web Framework

**Chosen**: FastAPI (Python 3.11)

**Rationale**:
- Lightweight and modern async framework (constitution principle VIII: Simplicity First)
- Auto-generates OpenAPI documentation (reduces manual contract maintenance)
- Native async/await support for database and SSH operations
- Excellent performance for REST APIs
- Minimal boilerplate compared to Django
- Strong typing with Pydantic (input validation built-in)

**Alternatives Considered**:
- **Flask**: Mature but synchronous by default, requires extensions for async, no auto-docs
- **Django**: Too heavyweight for MVP backend-only API, includes ORM/admin/templates we don't need
- **Node.js + Express**: Would work but team familiarity with Python + ecosystem maturity favors Python

**Decision Driver**: Simplicity + async support + auto-docs + minimal dependencies

---

## Decision 2: Database ORM

**Chosen**: SQLAlchemy 2.0 with Psycopg2 driver

**Rationale**:
- Industry standard Python ORM with mature PostgreSQL support
- Declarative models map cleanly to spec entities (Tenant, User, Extension, ApplyAuditLog)
- Supports connection pooling for performance
- Alembic migrations for schema versioning
- Async support via sqlalchemy.ext.asyncio (compatible with FastAPI async patterns)

**Alternatives Considered**:
- **Raw SQL with Psycopg2**: More control but increases boilerplate and error-prone query construction
- **Peewee**: Simpler but less mature, smaller ecosystem
- **Django ORM**: Tied to Django framework (rejected in Decision 1)

**Decision Driver**: Maturity + PostgreSQL support + migration tooling + async compatibility

---

## Decision 3: Asterisk Command Execution

**Chosen**: subprocess (Python stdlib)

**Rationale**:
- Portal runs co-located with Asterisk on 65.108.92.238 (same host)
- Execute `asterisk -rx` commands locally via subprocess.run()
- No SSH complexity (keys, passwords, connection pooling, network errors)
- Standard library (no external dependencies)
- Simpler error handling (exit codes, stdout/stderr capture)
- Aligns with constitution principle VIII (Simplicity First)

**Implementation Pattern**:
```python
import subprocess

def reload_pjsip():
    """Reload PJSIP module via local Asterisk CLI."""
    result = subprocess.run(
        ["asterisk", "-rx", "pjsip reload"],
        capture_output=True,
        text=True,
        timeout=10
    )
    if result.returncode != 0:
        raise AsteriskReloadError(result.stderr)
    return result.stdout
```

**Alternatives Considered**:
- **Paramiko (SSH)**: Over-engineering for co-located deployment, adds complexity and failure modes (SSH keys, network, auth)
- **Asterisk Manager Interface (AMI)**: More complex protocol, requires AMI enabled on Asterisk, overkill for simple reload commands
- **Asterisk REST Interface (ARI)**: Designed for call control, not config management

**Decision Driver**: Simplicity + co-located deployment + no external dependencies + constitution compliance

**Future Enhancement**: If portal later runs on separate host, can add SSH option (but MVP is local-first)

---

## Decision 4: Atomic File Write Strategy

**Chosen**: Python tempfile.NamedTemporaryFile + os.replace()

**Rationale**:
- Satisfies constitution principle III (Atomic File Operations)
- Pattern: write to temp file in same directory → os.replace() to final path (atomic on POSIX)
- Prevents partial writes if process crashes mid-write
- tempfile.NamedTemporaryFile automatically handles temp file creation and cleanup
- os.replace() is atomic on Linux (Asterisk runs on Ubuntu per spec)

**Implementation Pattern**:
```python
import tempfile
import os

def write_config_atomic(content: str, target_path: str):
    """Write config file atomically using temp file + rename."""
    dir_path = os.path.dirname(target_path)
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=dir_path,
        delete=False,
        suffix='.tmp'
    ) as tmp:
        tmp.write(content)
        tmp_name = tmp.name

    # Atomic rename (POSIX)
    os.replace(tmp_name, target_path)
```

**Alternatives Considered**:
- **Direct file.write()**: Not atomic, violates constitution
- **Write + fsync + rename**: More complex, os.replace already atomic on target platform
- **File locking**: Doesn't prevent partial writes on crash

**Decision Driver**: Constitution compliance + POSIX atomicity guarantee + simplicity

---

## Decision 5: Extension Allocation Algorithm

**Chosen**: Database query for minimum available extension with concurrency-safe retry

**Rationale**:
- Extension range: 1000-1999 (spec constraint)
- Algorithm: SELECT MIN(num) WHERE num NOT IN (SELECT extension_number FROM extensions) AND num BETWEEN 1000 AND 1999
- Handles gaps from deleted users (e.g., if 1000, 1002 exist, allocates 1001)
- **Concurrency safety**: UNIQUE constraint on extension.number + DB transaction + retry on conflict
- If two admins create users simultaneously, one will succeed, other will retry with next available extension
- Simple SQL query, no complex in-memory allocation logic

**Implementation Strategy**:
1. Start DB transaction
2. Generate range 1000-1999, query allocated extensions
3. Find first gap (lowest unallocated number)
4. Create extension record with UNIQUE constraint
5. If IntegrityError (duplicate number), retry from step 2
6. Commit transaction (user + extension created atomically)

**Concurrency Safety Pattern**:
```python
def allocate_extension(session, user_id, max_retries=5):
    for attempt in range(max_retries):
        # Find lowest available
        available = session.execute("""
            SELECT MIN(candidate)
            FROM generate_series(1000, 1999) AS candidate
            WHERE candidate NOT IN (SELECT number FROM extensions)
        """).scalar()

        if available is None:
            raise ExtensionPoolExhausted()

        try:
            # Attempt insert with UNIQUE constraint
            extension = Extension(number=available, user_id=user_id)
            session.add(extension)
            session.flush()  # Trigger constraint check
            return extension
        except IntegrityError:
            # Another transaction grabbed this number, retry
            session.rollback()
            continue

    raise MaxRetriesExceeded()
```

**Alternatives Considered**:
- **Sequential counter**: Doesn't handle gaps from deletes, wastes extension numbers
- **Random allocation**: Unpredictable, complicates troubleshooting
- **Pre-allocated pool table**: Over-engineering for 1000 extensions
- **SELECT FOR UPDATE**: Locks entire table, hurts concurrency (advisory lock better)

**Decision Driver**: Simplicity + gap handling + concurrency safety + retry resilience

---

## Decision 6: Configuration File Format

**Chosen**: Asterisk native .conf format (INI-style)

**Rationale**:
- Asterisk 22.7.0 requires native .conf format for PJSIP and dialplan
- PJSIP endpoint format: [endpoint-name] sections with key=value pairs
- Dialplan format: [context-name] with exten => statements
- No templating needed - direct string formatting sufficient for MVP

**PJSIP Template** (per extension):
```ini
[<extension>]
type=endpoint
context=synergy-internal
disallow=all
allow=ulaw,alaw
auth=<extension>
aors=<extension>

[<extension>]
type=auth
auth_type=userpass
password=<generated_secret>
username=<extension>

[<extension>]
type=aor
max_contacts=1
```

**Dialplan Template** (per extension):
```ini
[synergy-internal]
exten => <extension>,1,Dial(PJSIP/<extension>,25)
 same => n,Hangup()
```

**Alternatives Considered**:
- **Jinja2 templates**: Over-engineering for simple string formatting
- **JSON/YAML + converter**: Unnecessary abstraction layer

**Decision Driver**: Simplicity + direct Asterisk compatibility + minimal dependencies

---

## Decision 7: Apply Serialization Strategy

**Chosen**: Database-backed advisory lock (PostgreSQL)

**Rationale**:
- Prevent concurrent Apply operations (spec edge case: simultaneous apply)
- PostgreSQL advisory locks: pg_advisory_lock(session-level) or pg_try_advisory_lock(non-blocking)
- Apply service acquires lock before generation, releases after reload
- If second apply starts while first runs, either blocks (waits) or fails fast (try_lock)
- No external lock service needed (Redis, etc.)

**Implementation**:
```python
from sqlalchemy import select, func

def apply_config():
    # Try to acquire lock 12345 (arbitrary ID for apply operation)
    lock_acquired = db.execute(select(func.pg_try_advisory_lock(12345))).scalar()

    if not lock_acquired:
        raise ApplyInProgressError("Another apply operation is running")

    try:
        # Generate config, write files, reload Asterisk
        ...
    finally:
        # Release lock
        db.execute(select(func.pg_advisory_unlock(12345)))
```

**Alternatives Considered**:
- **File-based lock**: Harder to clean up on crash
- **In-memory lock (threading.Lock)**: Doesn't work across multiple API server instances
- **Redis distributed lock**: Adds dependency (violates simplicity principle)

**Decision Driver**: Simplicity + PostgreSQL built-in + crash recovery

---

## Decision 8: Testing Strategy

**Chosen**: pytest with pytest-asyncio

**Rationale**:
- pytest: Industry standard Python testing framework
- pytest-asyncio: Plugin for testing FastAPI async endpoints
- Test layers:
  - **Unit tests**: Services and generators (mocked DB and SSH)
  - **Integration tests**: Full flow with test DB + mocked SSH
  - **Contract tests**: API responses match OpenAPI spec (schemathesis)

**Test Database**:
- Separate test database created per test session
- Alembic migrations run before tests
- Fixtures for sample data (users, extensions)

**Mocking SSH**:
- Mock Paramiko SSHClient in tests
- Simulate reload success and failure scenarios
- No actual Asterisk server needed for test suite

**Alternatives Considered**:
- **unittest**: Less ergonomic than pytest, more boilerplate
- **nose/nose2**: Less active development than pytest

**Decision Driver**: Python ecosystem standard + async support + fixture system

---

## Decision 9: Environment Configuration

**Chosen**: python-dotenv for .env file loading

**Rationale**:
- Constitution principle VII: No hardcoded secrets
- .env file pattern: DATABASE_URL, ASTERISK_HOST, ASTERISK_SSH_USER, ASTERISK_SSH_KEY_PATH
- python-dotenv loads .env into os.environ automatically
- .env.example checked into git (template), actual .env gitignored
- Production uses system environment variables (no .env file)

**Example .env**:
```env
DATABASE_URL=postgresql://user:pass@77.42.28.222/pbx_portal
ASTERISK_HOST=65.108.92.238
ASTERISK_SSH_USER=asterisk
ASTERISK_SSH_KEY_PATH=/home/user/.ssh/id_rsa
```

**Alternatives Considered**:
- **Config files (YAML/JSON)**: Still requires secret management, .env simpler
- **Vault/secrets manager**: Over-engineering for MVP

**Decision Driver**: Simplicity + industry standard + constitution compliance

---

## Decision 10: SIP Secret Generation

**Chosen**: Python secrets module (cryptographically secure random)

**Rationale**:
- Each extension needs SIP password for PJSIP auth
- Generate on user creation: secrets.token_urlsafe(16) → 22-char random string
- Cryptographically secure (not predictable like random.randint)
- URL-safe base64 (no special chars that break Asterisk config)
- Stored in Extension table, written to PJSIP auth section

**Implementation**:
```python
import secrets

def generate_sip_secret() -> str:
    """Generate cryptographically secure SIP password."""
    return secrets.token_urlsafe(16)  # e.g., "kJ8n3mQ-x7Lp9Rt2"
```

**Alternatives Considered**:
- **UUID**: Less entropy than token_urlsafe, longer
- **random.randint**: Not cryptographically secure
- **User-provided password**: Adds complexity, weak passwords risk

**Decision Driver**: Security + simplicity + Asterisk compatibility

---

## Summary of Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Web Framework | FastAPI (Python 3.11) | Async, auto-docs, lightweight |
| Database ORM | SQLAlchemy 2.0 + Psycopg2 | Mature, async, migrations |
| Asterisk Commands | subprocess (stdlib) | Co-located, simple, no SSH complexity |
| Atomic Writes | tempfile + os.replace | POSIX atomic guarantee |
| Extension Allocation | SQL MIN query | Simple, handles gaps, concurrency-safe |
| Config Format | Native Asterisk .conf | Direct compatibility |
| Apply Serialization | PostgreSQL advisory locks | Built-in, no extra dependency |
| Testing | pytest + pytest-asyncio | Standard, async support |
| Secrets Management | python-dotenv | Simple .env pattern |
| SIP Secrets | secrets.token_urlsafe | Cryptographically secure |

**Constitution Compliance**: All decisions align with Principle VIII (Simplicity First) - minimal dependencies, standard tools, no over-engineering.

---

## Open Questions Resolved

All technical unknowns from initial planning phase have been researched and decided. No remaining NEEDS CLARIFICATION items.

Ready to proceed to Phase 1 (data model, contracts, quickstart).
