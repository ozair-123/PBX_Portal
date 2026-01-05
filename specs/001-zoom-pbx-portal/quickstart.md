# Quickstart Guide: Zoom-Style PBX Management Portal

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data Model**: [data-model.md](./data-model.md) | **API Spec**: [contracts/openapi.yaml](./contracts/openapi.yaml)

## Overview

This guide helps developers get the Zoom-style PBX management portal up and running in under 15 minutes. You'll set up the development environment, database, Asterisk integration, and verify the system works end-to-end.

**Prerequisites**:
- Linux server (Ubuntu 22.04+ or Debian 12+) or WSL2 on Windows
- Python 3.12+
- PostgreSQL 16.11+
- MariaDB 10.11+
- Asterisk 22.7.0+ (with PJSIP Realtime and AMI enabled)
- Git

---

## 1. Clone Repository

```bash
git clone <repository-url>
cd PBX_Client_Web
git checkout 001-zoom-pbx-portal
```

---

## 2. Install Dependencies

### System Dependencies (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip postgresql mariadb-server
```

### Python Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows WSL: source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected `requirements.txt` contents** (based on plan.md):
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
mysql-connector-python==8.0.33
pydantic==2.4.2
pydantic-settings==2.0.3
python-dotenv==1.0.0
alembic==1.12.1
passlib[bcrypt]==1.7.4
argon2-cffi==23.1.0
cryptography==41.0.7
python-jose[cryptography]==3.3.0
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

---

## 3. Database Setup

### PostgreSQL (Application Database)

```bash
# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE pbx_portal;
CREATE USER pbx_admin WITH PASSWORD 'SecurePassword123';
GRANT ALL PRIVILEGES ON DATABASE pbx_portal TO pbx_admin;
\q
```

### MariaDB (Asterisk PJSIP Realtime)

```bash
# Create database and user
sudo mysql
```

```sql
CREATE DATABASE asterisk;
CREATE USER 'asterisk'@'localhost' IDENTIFIED BY 'AsteriskPassword456';
GRANT ALL PRIVILEGES ON asterisk.* TO 'asterisk'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Create PJSIP Realtime tables**:

```bash
mysql -u asterisk -p asterisk < scripts/sql/pjsip_realtime_schema.sql
```

**Expected schema** (`scripts/sql/pjsip_realtime_schema.sql`):
```sql
-- ps_endpoints: SIP endpoint configuration
CREATE TABLE IF NOT EXISTS ps_endpoints (
    id VARCHAR(255) PRIMARY KEY,
    transport VARCHAR(255),
    aors VARCHAR(255),
    auth VARCHAR(255),
    context VARCHAR(255),
    disallow VARCHAR(255),
    allow VARCHAR(255),
    direct_media VARCHAR(10) DEFAULT 'no',
    callerid VARCHAR(255)
);

-- ps_auths: Authentication credentials
CREATE TABLE IF NOT EXISTS ps_auths (
    id VARCHAR(255) PRIMARY KEY,
    auth_type VARCHAR(50) DEFAULT 'userpass',
    password VARCHAR(255),
    username VARCHAR(255)
);

-- ps_aors: Address of Record
CREATE TABLE IF NOT EXISTS ps_aors (
    id VARCHAR(255) PRIMARY KEY,
    max_contacts INT DEFAULT 1,
    remove_existing VARCHAR(10) DEFAULT 'yes',
    qualify_frequency INT DEFAULT 60
);
```

---

## 4. Environment Configuration

Create `.env` file in repository root:

```bash
cp .env.example .env
nano .env
```

**`.env` contents**:
```env
# PostgreSQL (Application Database)
DATABASE_URL=postgresql://pbx_admin:SecurePassword123@localhost:5432/pbx_portal

# MariaDB (Asterisk PJSIP Realtime)
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=asterisk
MARIADB_PASSWORD=AsteriskPassword456
MARIADB_DATABASE=asterisk

# Asterisk AMI
ASTERISK_AMI_HOST=localhost
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USER=admin
ASTERISK_AMI_SECRET=AmiSecretPassword789

# Security
FERNET_KEY=<generate-with-python-cryptography.fernet.Fernet.generate_key()>
JWT_SECRET_KEY=<generate-random-32-byte-base64-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
APP_ENV=development
LOG_LEVEL=INFO
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Asterisk Configuration Paths
ASTERISK_CONFIG_DIR=/etc/asterisk
ASTERISK_GENERATED_INBOUND=/etc/asterisk/extensions.d/synergycall/generated_inbound.conf
ASTERISK_GENERATED_INTERNAL=/etc/asterisk/extensions.d/synergycall/generated_internal.conf
ASTERISK_GENERATED_OUTBOUND=/etc/asterisk/extensions.d/synergycall/generated_outbound.conf
```

**Generate encryption keys**:
```bash
python3 -c "from cryptography.fernet import Fernet; print(f'FERNET_KEY={Fernet.generate_key().decode()}')"
python3 -c "import secrets; print(f'JWT_SECRET_KEY={secrets.token_urlsafe(32)}')"
```

Copy the output to `.env`.

---

## 5. Database Migrations

Run Alembic migrations to create application tables:

```bash
alembic upgrade head
```

**Expected output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial tenant/user/extension schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, Add devices table
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, Add DIDs table
INFO  [alembic.runtime.migration] Running upgrade 003 -> 004, Add trunks and outbound_policies
INFO  [alembic.runtime.migration] Running upgrade 004 -> 005, Add self-service fields to users
INFO  [alembic.runtime.migration] Running upgrade 005 -> 006, Add audit_logs table
INFO  [alembic.runtime.migration] Running upgrade 006 -> 007, Extend tenant and user tables
```

**Verify tables created**:
```bash
psql postgresql://pbx_admin:SecurePassword123@localhost:5432/pbx_portal -c "\dt"
```

Expected tables: `tenants`, `users`, `devices`, `dids`, `trunks`, `outbound_policies`, `apply_jobs`, `audit_logs`, `alembic_version`.

---

## 6. Asterisk Configuration

### AMI Setup

Edit `/etc/asterisk/manager.conf`:

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[admin]
secret = AmiSecretPassword789
permit = 127.0.0.1/255.255.255.255
read = all
write = all
```

Reload AMI:
```bash
sudo asterisk -rx "manager reload"
```

### PJSIP Realtime Configuration

Edit `/etc/asterisk/extconfig.conf`:

```ini
[settings]
ps_endpoints => mysql,asterisk,ps_endpoints
ps_auths => mysql,asterisk,ps_auths
ps_aors => mysql,asterisk,ps_aors
```

Edit `/etc/asterisk/res_config_mysql.conf`:

```ini
[general]
dbhost = localhost
dbname = asterisk
dbuser = asterisk
dbpass = AsteriskPassword456
dbport = 3306
dbsock = /var/run/mysqld/mysqld.sock
```

Reload PJSIP:
```bash
sudo asterisk -rx "module reload res_pjsip.so"
sudo asterisk -rx "module reload res_config_mysql.so"
```

### Dialplan Include Files

Create directory for portal-generated configs:

```bash
sudo mkdir -p /etc/asterisk/extensions.d/synergycall
sudo chown $USER:$USER /etc/asterisk/extensions.d/synergycall
```

Edit `/etc/asterisk/extensions.conf` (add includes):

```ini
[general]
static=yes
writeprotect=no

; Include portal-generated dialplans
#include extensions.d/synergycall/generated_inbound.conf
#include extensions.d/synergycall/generated_internal.conf
#include extensions.d/synergycall/generated_outbound.conf

[default]
exten => _X.,1,NoOp(Unhandled call: ${EXTEN})
 same => n,Hangup()
```

Reload dialplan:
```bash
sudo asterisk -rx "dialplan reload"
```

---

## 7. Seed Database (Optional)

Create platform admin user and demo tenant:

```bash
python3 scripts/seed_db.py
```

**Expected `scripts/seed_db.py`** (create if doesn't exist):
```python
import asyncio
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.tenant import Tenant
from src.models.user import User
from src.auth.password import PasswordHasher
from src.config import settings

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)

def seed():
    session = Session()

    # Create demo tenant
    tenant = Tenant(
        id=uuid4(),
        name="Demo Corporation",
        ext_min=1000,
        ext_max=1999,
        ext_next=1000,
        status="active"
    )
    session.add(tenant)

    # Create platform admin
    hasher = PasswordHasher()
    admin = User(
        id=uuid4(),
        tenant_id=tenant.id,
        username="admin",
        email="admin@demo.com",
        password_hash=hasher.hash("AdminPassword123!"),
        full_name="Platform Administrator",
        role="platform_admin",
        status="active",
        extension=1000
    )
    session.add(admin)

    # Increment extension counter
    tenant.ext_next = 1001

    session.commit()
    print(f"✅ Created tenant: {tenant.name} (ID: {tenant.id})")
    print(f"✅ Created admin user: {admin.email} / AdminPassword123!")
    print(f"   Extension: {admin.extension}")
    session.close()

if __name__ == "__main__":
    seed()
```

Run:
```bash
python3 scripts/seed_db.py
```

---

## 8. Start Development Server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Will watch for changes in these directories: ['/path/to/PBX_Client_Web']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 9. Verify Installation

### Test Health Check

```bash
curl http://localhost:8000/api/v1/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "ok", "latency_ms": 5.2},
    "mariadb": {"status": "ok", "latency_ms": 3.8},
    "asterisk_ami": {"status": "ok", "connected": true},
    "disk_space": {"status": "ok", "free_gb": 45.7, "percent_used": 35.2}
  }
}
```

### Test Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com", "password": "AdminPassword123!"}'
```

**Expected response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "...",
    "email": "admin@demo.com",
    "full_name": "Platform Administrator",
    "role": "platform_admin",
    "extension": 1000
  }
}
```

Save the `access_token` for subsequent requests.

### Test User Creation

```bash
export TOKEN="<access_token_from_login>"

curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@demo.com",
    "full_name": "John Doe",
    "password": "UserPassword123!",
    "role": "end_user",
    "voicemail_enabled": true
  }'
```

**Expected response**:
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "john.doe@demo.com",
  "email": "john.doe@demo.com",
  "full_name": "John Doe",
  "role": "end_user",
  "status": "active",
  "extension": 1001,
  "voicemail_enabled": true,
  "dnd_enabled": false,
  "created_at": "2026-01-05T10:00:00Z"
}
```

**Auto-assigned extension**: Notice extension `1001` was automatically assigned from tenant's extension pool.

### Test Device Creation

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "456e7890-e89b-12d3-a456-426614174001",
    "label": "Desk Phone",
    "transport": "udp",
    "codecs": ["ulaw", "alaw"]
  }'
```

**Expected response** (SIP password shown ONCE):
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174002",
  "user_id": "456e7890-e89b-12d3-a456-426614174001",
  "label": "Desk Phone",
  "sip_username": "1001-desk",
  "sip_password": "RandomSecure123!",
  "transport": "udp",
  "codecs": ["ulaw", "alaw"],
  "enabled": true
}
```

**⚠️ IMPORTANT**: Save the SIP password immediately - it will never be shown again.

### Test Apply Operation

```bash
curl -X POST http://localhost:8000/api/v1/apply \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response**:
```json
{
  "id": "901e2345-e89b-12d3-a456-426614174006",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "actor_id": "...",
  "status": "RUNNING",
  "created_at": "2026-01-05T10:05:00Z"
}
```

Wait a few seconds, then check apply job status:

```bash
curl http://localhost:8000/api/v1/apply/jobs/901e2345-e89b-12d3-a456-426614174006 \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response**:
```json
{
  "id": "901e2345-e89b-12d3-a456-426614174006",
  "status": "SUCCESS",
  "started_at": "2026-01-05T10:05:00Z",
  "ended_at": "2026-01-05T10:05:05Z",
  "diff_summary": "Added 1 user, 1 device",
  "config_files": [
    "/etc/asterisk/extensions.d/synergycall/generated_internal.conf"
  ]
}
```

### Test SIP Registration

Configure a SIP softphone (e.g., Zoiper, Linphone, X-Lite) with:
- **SIP Username**: `1001-desk` (from device creation response)
- **SIP Password**: `RandomSecure123!` (from device creation response)
- **SIP Server**: `<your-asterisk-server-ip>:5060`
- **Transport**: UDP

After registering, check device status:

```bash
curl http://localhost:8000/api/v1/devices/789e0123-e89b-12d3-a456-426614174002/status \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response** (if device registered):
```json
{
  "device_id": "789e0123-e89b-12d3-a456-426614174002",
  "sip_username": "1001-desk",
  "registered": true,
  "contact_uri": "sip:1001-desk@192.168.1.100:5060",
  "user_agent": "Zoiper v5.4.9",
  "expires": 3600,
  "last_registration": "2026-01-05T10:10:00Z"
}
```

---

## 10. Access Frontend

Open browser: `http://localhost:8000`

**Expected**: Web UI showing login page.

Login with:
- **Email**: `admin@demo.com`
- **Password**: `AdminPassword123!`

**Dashboard should show**:
- Tenant: Demo Corporation
- Users: 2 (admin, john.doe)
- Devices: 1 (Desk Phone)
- Extension Range: 1000-1999
- Next Extension: 1002

---

## 11. Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires database)
pytest tests/integration/ -v

# All tests
pytest -v

# With coverage
pytest --cov=src --cov-report=html
```

**Expected output** (example):
```
tests/unit/test_user_service.py::test_create_user PASSED
tests/unit/test_extension_allocator.py::test_allocate_extension PASSED
tests/integration/test_user_api.py::test_create_user_endpoint PASSED
tests/integration/test_apply_api.py::test_apply_configuration PASSED

======================== 45 passed in 12.34s ========================
```

---

## 12. Troubleshooting

### Database Connection Errors

**Error**: `psycopg2.OperationalError: could not connect to server`

**Fix**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection
psql postgresql://pbx_admin:SecurePassword123@localhost:5432/pbx_portal -c "SELECT 1;"
```

### AMI Connection Errors

**Error**: `Asterisk AMI connection failed`

**Fix**:
```bash
# Verify AMI is enabled
sudo asterisk -rx "manager show settings"

# Check credentials in /etc/asterisk/manager.conf
sudo cat /etc/asterisk/manager.conf | grep -A5 '\[admin\]'

# Test AMI connection
telnet localhost 5038
# Enter:
# Action: Login
# Username: admin
# Secret: AmiSecretPassword789
```

### PJSIP Realtime Not Working

**Error**: `Device not found in PJSIP Realtime`

**Fix**:
```bash
# Verify MariaDB connection
mysql -u asterisk -p asterisk -e "SELECT * FROM ps_endpoints;"

# Check Asterisk sees Realtime config
sudo asterisk -rx "pjsip show endpoints"

# Reload PJSIP
sudo asterisk -rx "module reload res_pjsip.so"
```

### Apply Operation Fails

**Error**: `Apply job status: FAILED`

**Fix**:
```bash
# Check apply job error details
curl http://localhost:8000/api/v1/apply/jobs/<job_id> -H "Authorization: Bearer $TOKEN"

# Check Asterisk logs
sudo tail -f /var/log/asterisk/full

# Verify generated config files
cat /etc/asterisk/extensions.d/synergycall/generated_internal.conf

# Test dialplan reload manually
sudo asterisk -rx "dialplan reload"
```

### Extension Pool Exhausted

**Error**: `Extension pool exhausted for tenant`

**Fix**:
```bash
# Check tenant extension range
psql postgresql://pbx_admin:SecurePassword123@localhost:5432/pbx_portal -c \
  "SELECT name, ext_min, ext_max, ext_next FROM tenants;"

# Expand extension range (platform admin only)
curl -X PATCH http://localhost:8000/api/v1/tenants/<tenant_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ext_max": 2999}'
```

---

## 13. Development Workflow

### Making Changes

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make code changes** in `src/`

3. **Run tests**:
   ```bash
   pytest -v
   ```

4. **Generate migration** (if models changed):
   ```bash
   alembic revision --autogenerate -m "Add new field to users"
   alembic upgrade head
   ```

5. **Test manually** with curl or frontend

6. **Commit changes**:
   ```bash
   git add .
   git commit -m "Add feature: <description>"
   ```

### Debugging Tips

**Enable debug logging**:
Edit `.env`:
```env
LOG_LEVEL=DEBUG
```

Restart server to see verbose SQL queries and API requests.

**Use IPython for interactive debugging**:
```bash
pip install ipython
ipython
```

```python
from src.database import SessionLocal
from src.models.user import User

session = SessionLocal()
users = session.query(User).all()
for user in users:
    print(user.email, user.extension)
```

**Test Asterisk dialplan**:
```bash
# Test dialplan parsing
sudo asterisk -rx "dialplan show"

# Test specific extension
sudo asterisk -rx "dialplan show 1001@portal-internal"

# Originate test call
sudo asterisk -rx "channel originate PJSIP/1001-desk application Playback demo-congrats"
```

---

## 14. Next Steps

Now that your development environment is working:

1. **Read the spec**: [spec.md](./spec.md) - understand user stories and requirements
2. **Read the plan**: [plan.md](./plan.md) - understand architecture decisions
3. **Explore API docs**: Visit `http://localhost:8000/docs` (FastAPI auto-generated Swagger UI)
4. **Review data model**: [data-model.md](./data-model.md) - understand entities and relationships
5. **Run `/sp.tasks`**: Generate implementation tasks breakdown
6. **Start implementing**: Pick a P1 user story and start coding!

---

## 15. Production Deployment Notes

**⚠️ NOT FOR PRODUCTION USE YET** - This is a development setup.

For production:
- Use systemd service instead of `uvicorn --reload`
- Configure HTTPS with reverse proxy (nginx/Apache)
- Use production-grade PostgreSQL/MariaDB (separate servers, replication)
- Set strong passwords and rotate JWT secrets
- Configure firewall rules (block AMI port 5038 from internet)
- Enable database backups
- Set `APP_ENV=production` in `.env`
- Review security checklist in spec.md (FR-040 through FR-048)

See deployment documentation (coming in future phases).

---

## Quick Reference

**Start development server**:
```bash
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Run migrations**:
```bash
alembic upgrade head
```

**Run tests**:
```bash
pytest -v
```

**Check Asterisk status**:
```bash
sudo asterisk -rx "pjsip show endpoints"
sudo asterisk -rx "dialplan show"
```

**API Documentation**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

**Log Locations**:
- Application logs: stdout (or `/var/log/pbx-portal/app.log` in production)
- Asterisk logs: `/var/log/asterisk/full`
- PostgreSQL logs: `/var/log/postgresql/postgresql-16-main.log`

---

**Need help?** Check:
- [spec.md](./spec.md) - Feature requirements
- [plan.md](./plan.md) - Technical architecture
- [data-model.md](./data-model.md) - Database schema
- [contracts/openapi.yaml](./contracts/openapi.yaml) - API endpoints

**Questions?** File an issue or contact the team.
