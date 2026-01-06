"""add_phone_number_model

Revision ID: 2b45d8dc907d
Revises: 5be0213f264b
Create Date: 2026-01-06 14:36:09.042054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b45d8dc907d'
down_revision: Union[str, None] = '5be0213f264b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create phone_numbers table
    op.create_table(
        'phone_numbers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('number', sa.String(16), nullable=False),
        sa.Column('status', sa.Enum('UNASSIGNED', 'ALLOCATED', 'ASSIGNED', name='phonenumberstatus'), nullable=False, server_default='UNASSIGNED'),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.String(255), nullable=True),
        sa.Column('provider_metadata', sa.dialects.postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('number', name='uq_phone_numbers_number'),
        sa.CheckConstraint("number ~ '^\\+[1-9]\\d{1,14}$'", name='phone_number_e164_format'),
        sa.CheckConstraint(
            "(status = 'UNASSIGNED' AND tenant_id IS NULL) OR (status IN ('ALLOCATED', 'ASSIGNED') AND tenant_id IS NOT NULL)",
            name='phone_number_tenant_consistency'
        ),
    )

    # Create indexes
    op.create_index('idx_phone_numbers_number', 'phone_numbers', ['number'], unique=True)
    op.create_index('idx_phone_numbers_status', 'phone_numbers', ['status'])
    op.create_index('idx_phone_numbers_tenant_id', 'phone_numbers', ['tenant_id'])
    op.create_index('idx_phone_numbers_tenant_status', 'phone_numbers', ['tenant_id', 'status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_phone_numbers_tenant_status', table_name='phone_numbers')
    op.drop_index('idx_phone_numbers_tenant_id', table_name='phone_numbers')
    op.drop_index('idx_phone_numbers_status', table_name='phone_numbers')
    op.drop_index('idx_phone_numbers_number', table_name='phone_numbers')

    # Drop table
    op.drop_table('phone_numbers')

    # Drop enum
    op.execute('DROP TYPE phonenumberstatus')
