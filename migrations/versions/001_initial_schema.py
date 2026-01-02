"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_tenant_id'), 'users', ['tenant_id'], unique=False)

    # Create extensions table
    op.create_table('extensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('number >= 1000 AND number <= 1999', name='extension_number_range'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('number'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_extensions_number'), 'extensions', ['number'], unique=True)

    # Create apply_audit_logs table
    op.create_table('apply_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('triggered_by', sa.String(length=255), nullable=False),
        sa.Column('outcome', sa.String(length=50), nullable=False),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('files_written', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('reload_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("outcome IN ('success', 'failure')", name='outcome_check'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_apply_audit_logs_triggered_at'), 'apply_audit_logs', ['triggered_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_apply_audit_logs_triggered_at'), table_name='apply_audit_logs')
    op.drop_table('apply_audit_logs')
    op.drop_index(op.f('ix_extensions_number'), table_name='extensions')
    op.drop_table('extensions')
    op.drop_index(op.f('ix_users_tenant_id'), table_name='users')
    op.drop_table('users')
    op.drop_table('tenants')
