"""Test Apply workflow and dialplan generation for DID routing."""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from src.database import engine, get_db
from src.config_generator.dialplan_generator import DialplanGenerator
from src.config_generator.inbound_router import InboundRouter
from src.models import PhoneNumber, DIDAssignment, PhoneNumberStatus, User, Tenant

print("=" * 80)
print("DID Apply Workflow Testing")
print("=" * 80)

# Step 1: Query database for current state
print("\n[1] Current Database State")
print("-" * 80)

with engine.connect() as conn:
    # Get DIDs and assignments
    result = conn.execute(text("""
        SELECT
            pn.id as phone_id,
            pn.number,
            pn.status,
            pn.tenant_id,
            da.id as assignment_id,
            da.assigned_type,
            da.assigned_id,
            u.extension,
            u.name as user_name,
            t.name as tenant_name
        FROM phone_numbers pn
        LEFT JOIN did_assignments da ON pn.id = da.phone_number_id
        LEFT JOIN users u ON da.assigned_id = u.id AND da.assigned_type = 'USER'
        LEFT JOIN tenants t ON pn.tenant_id = t.id
        ORDER BY pn.number
    """))

    did_data = []
    for row in result:
        did_info = {
            "phone_id": str(row[0]),
            "number": row[1],
            "status": row[2],
            "tenant_id": str(row[3]) if row[3] else None,
            "assignment_id": str(row[4]) if row[4] else None,
            "assigned_type": row[5],
            "assigned_id": str(row[6]) if row[6] else None,
            "extension": row[7],
            "user_name": row[8],
            "tenant_name": row[9]
        }
        did_data.append(did_info)

        status_str = f"{did_info['status']}"
        if did_info['assigned_type']:
            status_str += f" -> {did_info['assigned_type']}"
            if did_info['extension']:
                status_str += f" (ext {did_info['extension']})"

        print(f"  {did_info['number']:20} {status_str:40} Tenant: {did_info['tenant_name'] or 'None'}")

# Step 2: Test InboundRouter dialplan generation
print("\n[2] Generate Inbound DID Routing Dialplan")
print("-" * 80)

# Prepare data for dialplan generation
db_session = next(get_db())

try:
    # Get all ASSIGNED DIDs with their assignments
    assignments = db_session.query(DIDAssignment).join(
        PhoneNumber,
        DIDAssignment.phone_number_id == PhoneNumber.id
    ).filter(
        PhoneNumber.status == PhoneNumberStatus.ASSIGNED
    ).all()

    print(f"Found {len(assignments)} assigned DIDs")

    # Convert to dict format expected by InboundRouter
    did_assignments_data = []
    for assignment in assignments:
        phone_number = assignment.phone_number

        assignment_dict = {
            "number": phone_number.number,
            "assigned_type": assignment.assigned_type.value,
            "assigned_id": str(assignment.assigned_id) if assignment.assigned_id else None,
            "assigned_value": assignment.assigned_value,
            "tenant_id": str(phone_number.tenant_id) if phone_number.tenant_id else None,
        }

        # For USER assignments, lookup extension and tenant context
        if assignment.assigned_type.value == "USER" and assignment.assigned_id:
            user = db_session.query(User).filter(User.id == assignment.assigned_id).first()
            tenant = db_session.query(Tenant).filter(Tenant.id == phone_number.tenant_id).first()

            if user and tenant:
                assignment_dict["extension"] = user.extension
                # Generate tenant context name (e.g., "tenant-acme")
                tenant_context = f"tenant-{tenant.name.lower().replace(' ', '-')}"
                assignment_dict["tenant_context"] = tenant_context

                print(f"  {phone_number.number} -> {tenant_context},{user.extension}")

        did_assignments_data.append(assignment_dict)

    # Generate dialplan
    if did_assignments_data:
        dialplan = InboundRouter.generate(did_assignments=did_assignments_data, users=[])

        print("\nGenerated Dialplan:")
        print("-" * 80)
        print(dialplan)
        print("-" * 80)
    else:
        print("\nNo DID assignments found - skipping dialplan generation")

finally:
    db_session.close()

# Step 3: Test full DialplanGenerator
print("\n[3] Generate Complete Dialplan (with Extensions + DIDs)")
print("-" * 80)

db_session = next(get_db())

try:
    # Get all data
    users = db_session.query(User).all()
    tenants = db_session.query(Tenant).all()
    assignments = db_session.query(DIDAssignment).join(
        PhoneNumber,
        DIDAssignment.phone_number_id == PhoneNumber.id
    ).filter(
        PhoneNumber.status == PhoneNumberStatus.ASSIGNED
    ).all()

    # Convert to dicts
    users_data = []
    for user in users:
        users_data.append({
            "id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "name": user.name,
            "email": user.email,
            "extension": user.extension,
            "role": user.role.value,
            "status": user.status.value,
            "dnd_enabled": user.dnd_enabled,
            "call_forward_destination": user.call_forward_destination,
            "voicemail_enabled": user.voicemail_enabled,
        })

    tenants_data = []
    for tenant in tenants:
        tenants_data.append({
            "id": str(tenant.id),
            "name": tenant.name,
            "ext_min": tenant.ext_min,
            "ext_max": tenant.ext_max,
            "ext_next": tenant.ext_next,
        })

    did_assignments_data = []
    for assignment in assignments:
        phone_number = assignment.phone_number
        tenant = next((t for t in tenants if t.id == phone_number.tenant_id), None)

        assignment_dict = {
            "number": phone_number.number,
            "assigned_type": assignment.assigned_type.value,
            "assigned_id": str(assignment.assigned_id) if assignment.assigned_id else None,
            "assigned_value": assignment.assigned_value,
            "tenant_id": str(phone_number.tenant_id) if phone_number.tenant_id else None,
        }

        if assignment.assigned_type.value == "USER" and assignment.assigned_id:
            user = next((u for u in users if u.id == assignment.assigned_id), None)
            if user and tenant:
                assignment_dict["extension"] = user.extension
                assignment_dict["tenant_context"] = f"tenant-{tenant.name.lower().replace(' ', '-')}"

        did_assignments_data.append(assignment_dict)

    print(f"Generating dialplan for:")
    print(f"  - {len(users_data)} users")
    print(f"  - {len(tenants_data)} tenants")
    print(f"  - {len(did_assignments_data)} DID assignments")

    # Generate complete dialplan
    full_dialplan = DialplanGenerator.generate_config(
        users_with_extensions=users_data,
        tenants=tenants_data,
        did_assignments=did_assignments_data,
    )

    print("\nComplete Dialplan Configuration:")
    print("=" * 80)
    print(full_dialplan)
    print("=" * 80)

    # Write to file for inspection
    output_file = "generated_dialplan.conf"
    with open(output_file, "w") as f:
        f.write(full_dialplan)
    print(f"\nDialplan written to: {output_file}")

finally:
    db_session.close()

# Step 4: Verify dialplan contains expected patterns
print("\n[4] Verify Dialplan Content")
print("-" * 80)

expected_patterns = [
    "[from-trunk-external]",  # Inbound DID context
    "exten =>",  # Extension patterns
]

missing_patterns = []
for pattern in expected_patterns:
    if pattern not in full_dialplan:
        missing_patterns.append(pattern)
        print(f"  [FAIL] Missing: {pattern}")
    else:
        print(f"  [OK] Found: {pattern}")

if not missing_patterns:
    print("\n[OK] All expected patterns found in dialplan!")
else:
    print(f"\n[FAIL] {len(missing_patterns)} patterns missing from dialplan")

# Step 5: Check for DID routing entries
print("\n[5] Verify DID Routing Entries")
print("-" * 80)

assigned_dids = [d for d in did_data if d['status'] == 'ASSIGNED']

if not assigned_dids:
    print("  [INFO] No ASSIGNED DIDs found - DID routing section will be empty")
else:
    for did in assigned_dids:
        if did['assigned_type'] == 'USER':
            number = did['number']
            extension = did['extension']

            # Look for routing entry in dialplan
            routing_pattern = f"exten => {number}"
            if routing_pattern in full_dialplan:
                print(f"  [OK] {number} -> ext {extension}: Found in dialplan")
            else:
                print(f"  [FAIL] {number} -> ext {extension}: NOT found in dialplan")

print("\n" + "=" * 80)
print("Apply Workflow Testing Complete!")
print("=" * 80)
