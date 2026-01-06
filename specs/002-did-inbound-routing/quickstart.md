# Quickstart: DID Inventory & Inbound Routing Management

**Feature**: DID Inventory & Inbound Routing Management
**Branch**: `002-did-inbound-routing`
**Date**: 2026-01-06

## Overview

This guide helps developers understand and implement the DID management feature for the PBX portal.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Existing PBX_Client_Web installation (Phase 1-4 complete)
- Platform admin account for testing

## Quick Start (5 minutes)

### 1. Run Database Migration

```bash
# Apply DID schema migration
alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\d phone_numbers"
psql $DATABASE_URL -c "\d did_assignments"
```

### 2. Test DID Import (Python Shell)

```python
from src.database import SessionLocal
from src.services.did_service import DIDService
from uuid import UUID

db = SessionLocal()

# Import test DIDs
result = DIDService.import_dids(
    session=db,
    dids=[
        {"number": "+15551234567", "provider": "Twilio", "metadata": {"account_sid": "AC123"}},
        {"number": "+15559876543", "provider": "Bandwidth", "metadata": {}},
    ],
    actor_id=UUID("your-platform-admin-user-id"),
)

print(result)  # {"imported": 2, "failed": 0, "errors": []}
db.close()
```

### 3. Test via API

```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@pbx.local", "password": "admin123"}' \
  | jq -r '.access_token')

# Import DIDs
curl -X POST http://localhost:8000/api/v1/dids/import \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dids": [
      {"number": "+15551112222", "provider": "Twilio"},
      {"number": "+15553334444", "provider": "Bandwidth"}
    ]
  }'

# List DIDs
curl -X GET "http://localhost:8000/api/v1/dids?status=UNASSIGNED" \
  -H "Authorization: Bearer $TOKEN"

# Allocate DID to tenant
DID_ID="<uuid-from-list>"
TENANT_ID="<your-tenant-uuid>"
curl -X PATCH "http://localhost:8000/api/v1/dids/$DID_ID/allocate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"tenant_id\": \"$TENANT_ID\"}"

# Assign DID to user
USER_ID="<your-user-uuid>"
curl -X POST "http://localhost:8000/api/v1/dids/$DID_ID/assign" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"assigned_type\": \"USER\", \"assigned_id\": \"$USER_ID\"}"

# Trigger Apply
curl -X POST http://localhost:8000/api/v1/apply \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": null, "force": false}'

# Check generated dialplan
cat /etc/asterisk/extensions_custom.conf
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                │
│  POST /dids/import   GET /dids   PATCH /dids/{id}/allocate    │
│  POST /dids/{id}/assign   DELETE /dids/{id}/assign            │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                     Service Layer                               │
│  DIDService.import_dids()   DIDService.allocate_to_tenant()    │
│  DIDService.assign_to_destination()   DIDService.unassign()    │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      Data Layer                                 │
│  PhoneNumber model (id, number, status, tenant_id)             │
│  DIDAssignment model (phone_number_id, assigned_type, etc.)    │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                  Configuration Generation                       │
│  InboundRouter.generate() → [from-trunk-external] context      │
│  ApplyService integrates DID assignments into dialplan         │
└─────────────────────────────────────────────────────────────────┘
```

## DID Lifecycle

```
1. Import → UNASSIGNED (platform admin)
2. Allocate → ALLOCATED (platform admin assigns to tenant)
3. Assign → ASSIGNED (tenant admin assigns to user/IVR/queue/external)
4. Apply → Dialplan generated with inbound routing
5. Unassign → ALLOCATED (tenant admin removes assignment)
6. Deallocate → UNASSIGNED (platform admin returns to global pool)
```

## Key Files

| Path | Purpose |
|------|---------|
| `src/models/phone_number.py` | PhoneNumber ORM model |
| `src/models/did_assignment.py` | DIDAssignment ORM model |
| `src/services/did_service.py` | Business logic (import, allocate, assign) |
| `src/api/v1/dids.py` | REST API endpoints |
| `src/schemas/phone_number.py` | Pydantic request/response schemas |
| `src/config_generator/inbound_router.py` | Dialplan generation |
| `alembic/versions/*_add_did_models.py` | Database migration |

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/test_services/test_did_service.py -v
pytest tests/test_api/test_dids.py -v
pytest tests/test_models/test_phone_number.py -v

# Test coverage
pytest --cov=src/services/did_service --cov=src/api/v1/dids
```

## Common Operations

### Bulk Import from CSV

```python
import csv
from src.services.did_service import DIDService

with open('dids.csv') as f:
    reader = csv.DictReader(f)
    dids = [{"number": row["number"], "provider": row["provider"]} for row in reader]

result = DIDService.import_dids(session=db, dids=dids, actor_id=admin_id)
print(f"Imported: {result['imported']}, Failed: {result['failed']}")
```

### Assign DID to Voicemail (EXTERNAL type)

```bash
curl -X POST "http://localhost:8000/api/v1/dids/$DID_ID/assign" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assigned_type": "EXTERNAL", "assigned_value": "VoiceMail(2000@tenant-acme)"}'
```

### Query DIDs for Tenant

```python
from src.models.phone_number import PhoneNumber

# Get all DIDs allocated to tenant
dids = session.query(PhoneNumber).filter(
    PhoneNumber.tenant_id == tenant_uuid,
    PhoneNumber.status.in_(['ALLOCATED', 'ASSIGNED'])
).all()
```

## Troubleshooting

### E.164 Validation Errors

```
Error: "Invalid E.164 format: 15551234567"
Solution: Add '+' prefix: "+15551234567"

Error: "Invalid E.164 format: +01234567890"
Solution: Remove leading zero after country code: "+1234567890"
```

### DID Already Assigned

```
Error: "DID +15551234567 is already assigned"
Cause: Unique constraint on phone_number_id violated
Solution: Unassign first: DELETE /dids/{id}/assign
```

### Cannot Deallocate DID

```
Error: "Cannot deallocate DID: currently assigned to user alice@example.com"
Cause: DIDAssignment exists
Solution: Unassign first, then deallocate
```

### Dialplan Not Generated

```
Symptom: DID assigned but not in extensions_custom.conf
Cause: Apply not triggered
Solution: POST /api/v1/apply to generate dialplan
```

## Performance Tips

1. **Bulk Import**: Use single transaction for 1000+ DIDs (30s target)
2. **Pagination**: Use `page_size=50` for large DID lists (avoid loading 1000+ at once)
3. **Indexes**: Queries on `status`, `tenant_id` use composite index for fast filtering
4. **Concurrent Assignments**: Database unique constraint prevents race conditions (no application-level locking needed)

## Security Checklist

- ✅ RBAC enforced at API layer (platform_admin for allocate/deallocate, tenant_admin for assign)
- ✅ Tenant isolation via query filters (`current_user.tenant_id`)
- ✅ E.164 validation prevents malformed numbers
- ✅ Audit logging captures all operations (actor_id, timestamp, source_ip)
- ✅ No hardcoded secrets (uses environment variables)

## Next Steps

1. Review [spec.md](spec.md) for complete requirements
2. Review [plan.md](plan.md) for implementation architecture
3. Review [data-model.md](data-model.md) for database schema details
4. Run `/sp.tasks` to generate actionable implementation tasks
5. Start with Phase 1: Data Models & Migrations

## Support

- **Documentation**: `/docs` endpoint (Swagger UI)
- **Issues**: Report bugs in project issue tracker
- **Questions**: See CLAUDE.md for development guidelines

---

**Quickstart Status**: ✅ Ready for developers
**Prerequisites**: ✅ Phase 1-4 complete
**Est. Setup Time**: 5 minutes
