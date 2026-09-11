"""002_phase4_auth_audit_review

Revision ID: 002_phase4_auth_audit_review
Revises: 001_phase2_core_domain
Create Date: 2026-09-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_phase4_auth_audit_review'
down_revision: Union[str, None] = '001_phase2_core_domain'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. users: add updated_at
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 2. documents: add created_by
    op.add_column('documents', sa.Column('created_by', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_documents_created_by_users',
        'documents', 'users',
        ['created_by'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_documents_created_by'), 'documents', ['created_by'], unique=False)

    # 3. land_records: add created_by and human review fields
    op.add_column('land_records', sa.Column('created_by', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_land_records_created_by_users',
        'land_records', 'users',
        ['created_by'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_land_records_created_by'), 'land_records', ['created_by'], unique=False)

    op.add_column('land_records', sa.Column('review_status', sa.String(length=50), server_default='PENDING_REVIEW', nullable=False))
    op.create_index(op.f('ix_land_records_review_status'), 'land_records', ['review_status'], unique=False)

    op.add_column('land_records', sa.Column('reviewed_by', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_land_records_reviewed_by_users',
        'land_records', 'users',
        ['reviewed_by'], ['id'],
        ondelete='SET NULL'
    )

    op.add_column('land_records', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('land_records', sa.Column('review_notes', sa.Text(), nullable=True))
    op.add_column('land_records', sa.Column('rejection_reason', sa.Text(), nullable=True))

    # 4. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('actor_user_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Uuid(), nullable=True),
        sa.Column('previous_state', sa.JSON(), nullable=True),
        sa.Column('new_state', sa.JSON(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_actor_user_id'), 'audit_logs', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)

def downgrade() -> None:
    # Drop audit_logs
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_user_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    # Drop land_records review and created_by columns
    op.drop_column('land_records', 'rejection_reason')
    op.drop_column('land_records', 'review_notes')
    op.drop_column('land_records', 'reviewed_at')
    op.drop_constraint('fk_land_records_reviewed_by_users', 'land_records', type_='foreignkey')
    op.drop_column('land_records', 'reviewed_by')
    op.drop_index(op.f('ix_land_records_review_status'), table_name='land_records')
    op.drop_column('land_records', 'review_status')
    op.drop_index(op.f('ix_land_records_created_by'), table_name='land_records')
    op.drop_constraint('fk_land_records_created_by_users', 'land_records', type_='foreignkey')
    op.drop_column('land_records', 'created_by')

    # Drop documents created_by
    op.drop_index(op.f('ix_documents_created_by'), table_name='documents')
    op.drop_constraint('fk_documents_created_by_users', 'documents', type_='foreignkey')
    op.drop_column('documents', 'created_by')

    # Drop users updated_at
    op.drop_column('users', 'updated_at')
