"""Bootstrap script to create initial platform admin user."""

import sys
import os
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import SessionLocal
from src.models.tenant import Tenant, TenantStatus
from src.models.user import User, UserRole, UserStatus
from src.auth.password import PasswordHasher

def bootstrap():
    """Create initial platform admin and default tenant."""
    db = SessionLocal()

    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@pbx.local").first()
        if existing_admin:
            print("❌ Admin user already exists!")
            return

        # Create default tenant
        print("Creating default tenant...")
        tenant = Tenant(
            id=uuid4(),
            name="Default Organization",
            ext_min=1000,
            ext_max=1999,
            ext_next=1000,
            status=TenantStatus.active,
        )
        db.add(tenant)
        db.flush()

        # Create platform admin user
        print("Creating platform admin user...")
        admin = User(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Platform Administrator",
            email="admin@pbx.local",
            password_hash=PasswordHasher.hash("admin123"),  # Change this password!
            role=UserRole.platform_admin,
            status=UserStatus.active,
            extension=1000,
            voicemail_enabled=False,
        )
        db.add(admin)

        # Update tenant ext_next
        tenant.ext_next = 1001

        db.commit()

        print("\n✅ Bootstrap complete!")
        print("\n📋 Login Credentials:")
        print("   Email:    admin@pbx.local")
        print("   Password: admin123")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
        print(f"\n🏢 Tenant ID: {tenant.id}")
        print(f"📞 Extension Range: {tenant.ext_min}-{tenant.ext_max}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    bootstrap()
