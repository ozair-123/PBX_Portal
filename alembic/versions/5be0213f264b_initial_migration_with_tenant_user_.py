"""Initial migration with tenant user audit and apply tables

Revision ID: 5be0213f264b
Revises:
Create Date: 2026-01-05 20:32:12.438014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5be0213f264b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (create_type=False to prevent automatic creation, we create them manually)
    tenant_status_enum = postgresql.ENUM('active', 'suspended', name='tenantstatus', create_type=False)
    tenant_status_enum.create(op.get_bind(), checkfirst=True)

    user_role_enum = postgresql.ENUM('platform_admin', 'tenant_admin', 'support', 'end_user', name='userrole', create_type=False)
    user_role_enum.create(op.get_bind(), checkfirst=True)

    user_status_enum = postgresql.ENUM('active', 'suspended', 'deleted', name='userstatus', create_type=False)
    user_status_enum.create(op.get_bind(), checkfirst=True)

    audit_action_enum = postgresql.ENUM('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'APPLY', name='auditaction', create_type=False)
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    apply_status_enum = postgresql.ENUM('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'ROLLED_BACK', name='applystatus', create_type=False)
    apply_status_enum.create(op.get_bind(), checkfirst=True)

    # Create tenants table (no foreign keys, so create first)
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('ext_min', sa.Integer(), nullable=False),
        sa.Column('ext_max', sa.Integer(), nullable=False),
        sa.Column('ext_next', sa.Integer(), nullable=False),
        sa.Column('default_inbound_destination', sa.String(255), nullable=True),
        sa.Column('outbound_policy_id', postgresql.UUID(as_uuid=True), nullable=True),  # FK will be added later when outbound_policies table exists
        sa.Column('status', tenant_status_enum, nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create users table (depends on tenants)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', user_role_enum, nullable=False, server_default='end_user'),
        sa.Column('status', user_status_enum, nullable=False, server_default='active'),
        sa.Column('extension', sa.Integer(), nullable=False),
        sa.Column('outbound_callerid', sa.String(20), nullable=True),
        sa.Column('voicemail_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('voicemail_pin_hash', sa.Text(), nullable=True),
        sa.Column('dnd_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('call_forward_destination', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Create audit_logs table (depends on tenants and users)
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', audit_action_enum, nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('before_json', postgresql.JSONB(), nullable=True),
        sa.Column('after_json', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('source_ip', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create index on timestamp for faster queries
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])

    # Create apply_jobs table (depends on tenants and users)
    op.create_table(
        'apply_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', apply_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('diff_summary', sa.Text(), nullable=True),
        sa.Column('config_files_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('apply_jobs')
    op.drop_index('ix_audit_logs_timestamp', 'audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop enums
    postgresql.ENUM(name='applystatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='auditaction').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='userstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='userrole').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='tenantstatus').drop(op.get_bind(), checkfirst=True)
