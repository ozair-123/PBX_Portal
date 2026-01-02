# Deployment Guide - PBX Control Portal MVP

This guide covers deploying the PBX Control Portal to the production Asterisk server at 65.108.92.238.

## Prerequisites

### Server Requirements
- Ubuntu Linux server at 65.108.92.238
- Asterisk 22.7.0 already installed and running
- Python 3.11+ installed
- Access to PostgreSQL at 77.42.28.222
- Root or sudo access for Asterisk configuration

### Database Requirements
- PostgreSQL server accessible at 77.42.28.222:5432
- Database `pbx_portal` created
- User with full permissions on `pbx_portal` database

## Deployment Steps

### 1. Prepare Server

SSH into the Asterisk server:
```bash
ssh user@65.108.92.238
```

Install Python dependencies:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

### 2. Clone Repository

```bash
cd /opt
sudo git clone <repository-url> pbx-portal
cd pbx-portal
sudo chown -R $USER:$USER /opt/pbx-portal
```

### 3. Configure Environment

Create and configure `.env` file:
```bash
cp .env.example .env
nano .env
```

Edit `.env` with actual credentials:
```env
# Database connection - REPLACE WITH ACTUAL CREDENTIALS
DATABASE_URL=postgresql://pbx_user:actual_password@77.42.28.222:5432/pbx_portal

# Logging
LOG_LEVEL=INFO
```

**Important**: Secure the `.env` file:
```bash
chmod 600 .env
```

### 4. Set Up Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Asterisk Include Directories

Create directories for generated configs:
```bash
sudo mkdir -p /etc/asterisk/pjsip.d/synergycall
sudo mkdir -p /etc/asterisk/extensions.d/synergycall
```

Set permissions so the application can write to these directories:
```bash
# Option 1: Run application as asterisk user (recommended)
sudo chown -R asterisk:asterisk /etc/asterisk/pjsip.d/synergycall
sudo chown -R asterisk:asterisk /etc/asterisk/extensions.d/synergycall

# Option 2: Give your user write access
sudo chown -R $USER:asterisk /etc/asterisk/pjsip.d/synergycall
sudo chown -R $USER:asterisk /etc/asterisk/extensions.d/synergycall
sudo chmod 775 /etc/asterisk/pjsip.d/synergycall
sudo chmod 775 /etc/asterisk/extensions.d/synergycall
```

### 6. Configure Asterisk to Include Generated Files

Edit PJSIP configuration to include generated endpoints:
```bash
sudo nano /etc/asterisk/pjsip.conf
```

Add at the end:
```ini
; Include auto-generated SIP endpoints from PBX Control Portal
#include pjsip.d/synergycall/*.conf
```

Edit extensions configuration to include generated dialplan:
```bash
sudo nano /etc/asterisk/extensions.conf
```

Add at the end:
```ini
; Include auto-generated dialplan from PBX Control Portal
#include extensions.d/synergycall/*.conf
```

Reload Asterisk to pick up include directives:
```bash
sudo asterisk -rx "module reload res_pjsip.so"
sudo asterisk -rx "dialplan reload"
```

### 7. Set Up Database

Run migrations to create schema:
```bash
source venv/bin/activate
alembic upgrade head
```

Verify tables were created:
```bash
psql -h 77.42.28.222 -U pbx_user -d pbx_portal -c "\dt"
```

Expected output:
```
                  List of relations
 Schema |      Name         | Type  |   Owner
--------+-------------------+-------+-----------
 public | alembic_version   | table | pbx_user
 public | apply_audit_logs  | table | pbx_user
 public | extensions        | table | pbx_user
 public | tenants           | table | pbx_user
 public | users             | table | pbx_user
```

Verify default tenant was created:
```bash
psql -h 77.42.28.222 -U pbx_user -d pbx_portal -c "SELECT * FROM tenants;"
```

### 8. Configure Asterisk CLI Permissions

The application needs to run `asterisk -rx` commands. Options:

**Option 1: Run as asterisk user (recommended)**
```bash
# Create systemd service to run as asterisk user (see step 9)
```

**Option 2: Add your user to asterisk group**
```bash
sudo usermod -a -G asterisk $USER
# Log out and back in for group change to take effect
```

**Option 3: Use sudo (less secure)**
```bash
# Configure passwordless sudo for asterisk commands
sudo visudo
# Add: youruser ALL=(ALL) NOPASSWD: /usr/sbin/asterisk
# Then modify src/asterisk/reloader.py to use sudo
```

### 9. Create Systemd Service (Production)

Create service file:
```bash
sudo nano /etc/systemd/system/pbx-portal.service
```

Service configuration:
```ini
[Unit]
Description=PBX Control Portal API
After=network.target postgresql.service asterisk.service
Requires=postgresql.service

[Service]
Type=simple
User=asterisk
Group=asterisk
WorkingDirectory=/opt/pbx-portal
Environment="PATH=/opt/pbx-portal/venv/bin"
EnvironmentFile=/opt/pbx-portal/.env
ExecStart=/opt/pbx-portal/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/etc/asterisk/pjsip.d/synergycall /etc/asterisk/extensions.d/synergycall

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pbx-portal
sudo systemctl start pbx-portal
```

Check status:
```bash
sudo systemctl status pbx-portal
```

View logs:
```bash
sudo journalctl -u pbx-portal -f
```

### 10. Test Deployment

Test health endpoint:
```bash
curl http://localhost:8000/health
```

Test from remote (if firewall allows):
```bash
curl http://65.108.92.238:8000/health
```

### 11. Configure Firewall (Optional)

If you need external access:
```bash
sudo ufw allow 8000/tcp
```

For internal-only access, use reverse proxy (nginx/traefik) or SSH tunnel.

## Post-Deployment Testing

### 1. Create Test User

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com"
  }'
```

### 2. Apply Configuration

```bash
curl -X POST http://localhost:8000/apply \
  -H "Content-Type: application/json" \
  -d '{
    "triggered_by": "deployment-test"
  }'
```

### 3. Verify Asterisk Configuration

```bash
# Check generated PJSIP config
cat /etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf

# Check generated dialplan
cat /etc/asterisk/extensions.d/synergycall/generated_routing.conf

# Verify Asterisk loaded the endpoints
sudo asterisk -rx "pjsip show endpoints"

# Verify dialplan loaded
sudo asterisk -rx "dialplan show synergy-internal"
```

### 4. Test SIP Registration

Use a SIP phone/softphone to register with:
- Server: 65.108.92.238
- Extension: 1000 (from test user creation)
- Password: (secret from API response)

## Troubleshooting

### Application won't start

Check logs:
```bash
sudo journalctl -u pbx-portal -n 50
```

Common issues:
- Database connection refused → Check DATABASE_URL in .env
- Permission denied → Check file permissions and asterisk group membership
- Port already in use → Change port in systemd service file

### Database connection errors

Test database connectivity:
```bash
psql -h 77.42.28.222 -U pbx_user -d pbx_portal -c "SELECT 1"
```

### Asterisk reload failures

Check Asterisk is running:
```bash
sudo asterisk -rx "core show version"
```

Check application has permission to run asterisk commands:
```bash
asterisk -rx "core show version"  # Should work without sudo
```

### Extension allocation fails

Check database constraints:
```bash
psql -h 77.42.28.222 -U pbx_user -d pbx_portal -c \
  "SELECT number FROM extensions ORDER BY number;"
```

### Apply operation fails with lock conflict

Check for stuck locks:
```bash
psql -h 77.42.28.222 -U pbx_user -d pbx_portal -c \
  "SELECT * FROM pg_locks WHERE locktype = 'advisory';"
```

If stuck, restart application:
```bash
sudo systemctl restart pbx-portal
```

## Monitoring

### Check Application Health

```bash
# Health check
curl http://localhost:8000/health

# Application logs
sudo journalctl -u pbx-portal --since "1 hour ago"

# Database connection
psql -h 77.42.28.222 -U pbx_user -d pbx_portal -c "SELECT COUNT(*) FROM users;"
```

### Check Asterisk Status

```bash
# Registered endpoints
sudo asterisk -rx "pjsip show endpoints"

# Active calls
sudo asterisk -rx "core show channels"

# Recent apply audit logs
psql -h 77.42.28.222 -U pbx_user -d pbx_portal -c \
  "SELECT id, triggered_at, triggered_by, outcome FROM apply_audit_logs ORDER BY triggered_at DESC LIMIT 10;"
```

## Backup and Recovery

### Database Backup

```bash
# Backup
pg_dump -h 77.42.28.222 -U pbx_user pbx_portal > pbx_portal_backup.sql

# Restore
psql -h 77.42.28.222 -U pbx_user pbx_portal < pbx_portal_backup.sql
```

### Configuration Backup

```bash
# Backup Asterisk generated configs
sudo tar czf asterisk_configs_backup.tar.gz \
  /etc/asterisk/pjsip.d/synergycall \
  /etc/asterisk/extensions.d/synergycall
```

## Security Considerations

1. **Database Credentials**: Never commit `.env` to version control
2. **File Permissions**: Ensure only authorized users can write to Asterisk config directories
3. **API Access**: Consider adding authentication (not included in MVP)
4. **Firewall**: Restrict port 8000 to internal network or use reverse proxy
5. **Logs**: Rotate logs and monitor for security events

## Rollback Procedure

If deployment fails:

```bash
# Stop service
sudo systemctl stop pbx-portal

# Remove generated Asterisk configs
sudo rm -f /etc/asterisk/pjsip.d/synergycall/generated_endpoints.conf
sudo rm -f /etc/asterisk/extensions.d/synergycall/generated_routing.conf

# Reload Asterisk
sudo asterisk -rx "module reload res_pjsip.so"
sudo asterisk -rx "dialplan reload"

# Rollback database (if needed)
alembic downgrade -1
```

## Support

For issues or questions:
- Check logs: `sudo journalctl -u pbx-portal -f`
- Review README.md for API documentation
- Check constitution.md for project principles
