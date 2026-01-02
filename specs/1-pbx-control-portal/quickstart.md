# Quickstart: PBX Control Portal MVP

**Feature**: PBX Control Portal MVP
**Branch**: 1-pbx-control-portal
**Date**: 2026-01-01

## Overview

This guide walks you through setting up and running the PBX Control Portal backend API for local development and testing.

**What you'll set up**:
- Python 3.11 development environment
- PostgreSQL database connection (to 77.42.28.222)
- SSH access to Asterisk server (65.108.92.238)
- FastAPI application running locally

**Time to complete**: ~15 minutes

---

## Prerequisites

### Required
- **Python 3.11** or higher
- **PostgreSQL database** at 77.42.28.222 (credentials required)
- **Asterisk 22.7.0** running locally on same host (65.108.92.238)
- **Git** (to clone repository)

**Note**: Portal runs co-located with Asterisk on 65.108.92.238 (no remote SSH needed)

### Asterisk Server Prerequisites (Manual Setup)
These must be configured on the local Asterisk server BEFORE running the portal:

1. **Include directories created**:
   ```bash
   sudo mkdir -p /etc/asterisk/pjsip.d/synergycall
   sudo mkdir -p /etc/asterisk/extensions.d/synergycall
   sudo chown asterisk:asterisk /etc/asterisk/pjsip.d/synergycall
   sudo chown asterisk:asterisk /etc/asterisk/extensions.d/synergycall
   ```

2. **Include directives added** to core Asterisk config:
   - In `/etc/asterisk/pjsip.conf`, add: `#include pjsip.d/synergycall/*.conf`
   - In `/etc/asterisk/extensions.conf`, add: `#include extensions.d/synergycall/*.conf`

3. **PJSIP transport configured** (UDP/TCP listener in `/etc/asterisk/pjsip.conf`)

4. **Portal user has permissions** to execute `asterisk -rx` commands (typically run portal as `asterisk` user or add to `asterisk` group)

---

## Step 1: Clone Repository

```bash
git clone <repository-url>
cd PBX_Client_Web
git checkout 1-pbx-control-portal
```

---

## Step 2: Install Python Dependencies

### Create virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected dependencies** (requirements.txt):
- fastapi
- uvicorn[standard]
- sqlalchemy[asyncio]
- psycopg2-binary
- alembic
- python-dotenv
- pydantic[email]
- pytest
- pytest-asyncio

---

## Step 3: Configure Environment Variables

### Copy template
```bash
cp .env.example .env
```

### Edit .env file
```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@77.42.28.222:5432/pbx_portal

# Application Configuration
LOG_LEVEL=INFO
```

**Security Notes**:
- `.env` is gitignored (never commit secrets)
- Portal runs as local user with permissions to execute `asterisk -rx` commands

---

## Step 4: Initialize Database

### Run migrations
```bash
alembic upgrade head
```

**This will**:
1. Create `tenants`, `users`, `extensions`, `apply_audit_logs` tables
2. Insert default tenant (ID: `a0000000-0000-0000-0000-000000000000`, Name: "Default")

### Verify migration success
```bash
alembic current
```

Expected output: `001_initial_schema (head)`

---

## Step 5: Start Development Server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Server should start**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Step 6: Verify Installation

### Access Swagger UI
Open browser: http://localhost:8000/docs

You should see FastAPI auto-generated API documentation with 4 endpoints:
- `POST /users` - Create user
- `GET /users` - List users
- `DELETE /users/{userId}` - Delete user
- `POST /apply` - Apply configuration

### Test API with curl

#### Create a user
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com"
  }'
```

**Expected response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "a0000000-0000-0000-0000-000000000000",
  "name": "Test User",
  "email": "test@example.com",
  "extension": {
    "number": 1000,
    "secret": "kJ8n3mQ-x7Lp9Rt2"
  },
  "created_at": "2026-01-01T10:00:00Z"
}
```

#### List users
```bash
curl http://localhost:8000/users
```

**Expected response** (200 OK):
```json
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "tenant_id": "a0000000-0000-0000-0000-000000000000",
      "name": "Test User",
      "email": "test@example.com",
      "extension": {
        "number": 1000,
        "secret": "kJ8n3mQ-x7Lp9Rt2"
      },
      "created_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

#### Apply configuration
```bash
curl -X POST http://localhost:8000/apply \
  -H "Content-Type: application/json" \
  -d '{
    "triggered_by": "admin@example.com"
  }'
```

**Expected response** (200 OK):
```json
{
  "message": "Configuration applied successfully",
  "audit_log_id": "880e8400-e29b-41d4-a716-446655440003",
  "files_written": [
    "/etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf",
    "/etc/asterisk/extensions.d/synergycall/generated_routing.conf"
  ],
  "reload_results": {
    "pjsip_reload": {
      "exit_code": 0,
      "stdout": "PJSIP reload completed"
    },
    "dialplan_reload": {
      "exit_code": 0,
      "stdout": "Dialplan reload completed"
    }
  },
  "users_applied": 1,
  "extensions_generated": 1
}
```

#### Verify generated config on local Asterisk server
```bash
cat /etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf
```

**Expected output**:
```ini
[1000]
type=endpoint
context=synergy-internal
disallow=all
allow=ulaw,alaw
auth=1000
aors=1000

[1000]
type=auth
auth_type=userpass
password=kJ8n3mQ-x7Lp9Rt2
username=1000

[1000]
type=aor
max_contacts=1
```

```bash
cat /etc/asterisk/extensions.d/synergycall/generated_routing.conf
```

**Expected output**:
```ini
[synergy-internal]
exten => 1000,1,Dial(PJSIP/1000,25)
 same => n,Hangup()
```

---

## Step 7: Run Tests

```bash
pytest tests/ -v
```

**Expected output**:
```
tests/unit/test_extension_allocator.py::test_allocate_first_extension PASSED
tests/unit/test_pjsip_generator.py::test_generate_endpoint_config PASSED
tests/unit/test_dialplan_generator.py::test_generate_dialplan_config PASSED
tests/integration/test_user_creation.py::test_create_user_allocates_extension PASSED
tests/integration/test_apply_flow.py::test_apply_generates_config PASSED
tests/contract/test_api_compliance.py::test_openapi_schema_valid PASSED

======================== 6 passed in 2.34s ========================
```

---

## Troubleshooting

### Database connection fails
**Error**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Solutions**:
- Verify PostgreSQL is running at 77.42.28.222
- Check DATABASE_URL in .env (correct host, port, credentials)
- Test connection: `psql postgresql://username:password@77.42.28.222:5432/pbx_portal`
- Check firewall allows port 5432 from your host

### Asterisk reload fails
**Error**: `Apply operation failed: Asterisk reload command failed`

**Solutions**:
- Verify Asterisk is running: `asterisk -rx 'core show version'`
- Check portal user has permission to run `asterisk -rx` commands (run as `asterisk` user or in `asterisk` group)
- Verify include directories exist and have correct permissions
- Check Asterisk logs: `tail -100 /var/log/asterisk/messages`
- If "Unable to connect to remote asterisk", verify `/var/run/asterisk/asterisk.ctl` exists

### Extension pool exhausted
**Error**: `Extension pool exhausted` when creating user

**Solutions**:
- Check database: `SELECT COUNT(*) FROM extensions;` (should be < 1000)
- Delete unused users to free extensions: `DELETE /users/{userId}`
- Run apply to remove deleted users from Asterisk: `POST /apply`

### Migration fails
**Error**: `alembic.util.exc.CommandError: Target database is not up to date`

**Solutions**:
- Check current version: `alembic current`
- Downgrade if needed: `alembic downgrade base`
- Re-run migrations: `alembic upgrade head`
- Verify database user has CREATE TABLE permissions

---

## Development Workflow

### Typical iteration loop

1. **Make code changes** (models, services, API)
2. **Run tests**: `pytest tests/ -v`
3. **Start server** (if not already running with --reload): `uvicorn src.main:app --reload`
4. **Test via Swagger UI**: http://localhost:8000/docs
5. **Commit changes**: `git add . && git commit -m "feat: ..." `

### Database schema changes

1. **Edit models** in `src/models/`
2. **Generate migration**: `alembic revision --autogenerate -m "Add column X"`
3. **Review migration** in `migrations/versions/`
4. **Apply migration**: `alembic upgrade head`
5. **Test with new schema**: `pytest tests/`

### Testing apply without Asterisk running

For development/testing without real Asterisk running:

1. **Mock subprocess calls** in tests (already configured in test fixtures)
2. **Use environment variable**: `ASTERISK_MOCK=true` (disables real subprocess commands)
3. **Verify generated configs** in `/tmp/asterisk_mock/` (mock writes here instead)

---

## Next Steps

- **Create more users**: Test extension allocation (1000, 1001, 1002...)
- **Test edge cases**: Pool exhaustion (create 1000 users), concurrent apply
- **Register SIP client**: Use extension number + secret from API response
- **Make test calls**: Dial another extension (e.g., 1000 dials 1001)
- **Review audit logs**: Query `apply_audit_logs` table for apply history
- **Read implementation plan**: See [plan.md](plan.md) for architecture details

---

## Production Deployment Notes

**Not covered in this quickstart** (MVP is development-focused):

- Reverse proxy (nginx) for HTTPS
- API authentication/authorization (MVP assumes trusted network)
- Database connection pooling tuning
- Systemd service for auto-start
- Log rotation and monitoring
- High availability / load balancing
- Backup and disaster recovery

See production deployment guide (to be created post-MVP) for these topics.

---

## Summary

You've successfully:
- ✅ Installed Python dependencies
- ✅ Configured database and SSH access
- ✅ Run database migrations
- ✅ Started FastAPI server
- ✅ Created users via API
- ✅ Applied configuration to Asterisk
- ✅ Verified generated PJSIP and dialplan configs

**Ready for development**: Proceed to [tasks.md](tasks.md) for implementation task breakdown (run `/sp.tasks`).
