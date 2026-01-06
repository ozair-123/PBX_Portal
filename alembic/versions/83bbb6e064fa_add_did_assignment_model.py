"""add_did_assignment_model

Revision ID: 83bbb6e064fa
Revises: 2b45d8dc907d
Create Date: 2026-01-06 14:40:25.805421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83bbb6e064fa'
down_revision: Union[str, None] = '2b45d8dc907d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create did_assignments table
    op.create_table(
        'did_assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('phone_number_id', sa.UUID(), nullable=False),
        sa.Column('assigned_type', sa.Enum('USER', 'IVR', 'QUEUE', 'EXTERNAL', name='assignmenttype'), nullable=False),
        sa.Column('assigned_id', sa.UUID(), nullable=True),
        sa.Column('assigned_value', sa.String(255), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['phone_number_id'], ['phone_numbers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('phone_number_id', name='uq_did_assignments_phone_number_id'),
        sa.CheckConstraint(
            "(assigned_type IN ('USER', 'IVR', 'QUEUE') AND assigned_id IS NOT NULL AND assigned_value IS NULL) OR "
            "(assigned_type = 'EXTERNAL' AND assigned_id IS NULL AND assigned_value IS NOT NULL)",
            name='did_assignment_type_consistency'
        ),
    )

    # Create indexes
    op.create_index('idx_did_assignments_phone_number_id', 'did_assignments', ['phone_number_id'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_did_assignments_phone_number_id', table_name='did_assignments')

    # Drop table
    op.drop_table('did_assignments')

    # Drop enum
    op.execute('DROP TYPE assignmenttype')
