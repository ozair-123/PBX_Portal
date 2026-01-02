"""Default tenant

Revision ID: 002
Revises: 001
Create Date: 2026-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert default tenant
    op.execute("""
        INSERT INTO tenants (id, name, created_at)
        VALUES (
            'a0000000-0000-0000-0000-000000000000'::uuid,
            'Default',
            NOW()
        )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM tenants
        WHERE id = 'a0000000-0000-0000-0000-000000000000'::uuid
    """)
