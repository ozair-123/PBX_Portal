"""Create test data for DID management testing."""
import sys
sys.path.insert(0, '.')

from uuid import uuid4
from sqlalchemy import text
from src.database import engine
from src.auth.password import PasswordHasher

print("Creating test data...")

# Generate UUIDs
tenant_id = uuid4()
admin_id = uuid4()
user_id = uuid4()

with engine.begin() as conn:
    # Create tenant
    print(f"Creating tenant: {tenant_id}")
    conn.execute(text("""
        INSERT INTO tenants (id, name, ext_min, ext_max, ext_next, status, created_at, updated_at)
        VALUES (:id, :name, :ext_min, :ext_max, :ext_next, 'active', now(), now())
    """), {
        "id": str(tenant_id),
        "name": "Test Organization",
        "ext_min": 1000,
        "ext_max": 1999,
        "ext_next": 1002
    })

    # Create platform admin
    print(f"Creating platform admin: admin@pbx.local")
    admin_password_hash = PasswordHasher.hash("admin123")
    conn.execute(text("""
        INSERT INTO users (id, tenant_id, name, email, password_hash, role, status, extension,
                          voicemail_enabled, dnd_enabled, created_at, updated_at)
        VALUES (:id, :tenant_id, :name, :email, :password_hash, 'platform_admin', 'active', :extension,
                true, false, now(), now())
    """), {
        "id": str(admin_id),
        "tenant_id": str(tenant_id),
        "name": "Platform Administrator",
        "email": "admin@pbx.local",
        "password_hash": admin_password_hash,
        "extension": 1000
    })

    # Create tenant admin user
    print(f"Creating tenant admin: tenant@pbx.local")
    user_password_hash = PasswordHasher.hash("tenant123")
    conn.execute(text("""
        INSERT INTO users (id, tenant_id, name, email, password_hash, role, status, extension,
                          voicemail_enabled, dnd_enabled, created_at, updated_at)
        VALUES (:id, :tenant_id, :name, :email, :password_hash, 'tenant_admin', 'active', :extension,
                true, false, now(), now())
    """), {
        "id": str(user_id),
        "tenant_id": str(tenant_id),
        "name": "Tenant Administrator",
        "email": "tenant@pbx.local",
        "password_hash": user_password_hash,
        "extension": 1001
    })

print("\nTest data created successfully!")
print("\nLogin Credentials:")
print("  Platform Admin:")
print("    Email:    admin@pbx.local")
print("    Password: admin123")
print("  Tenant Admin:")
print("    Email:    tenant@pbx.local")
print("    Password: tenant123")
print(f"\nTenant ID: {tenant_id}")
print(f"Admin ID:  {admin_id}")
print(f"User ID:   {user_id}")
