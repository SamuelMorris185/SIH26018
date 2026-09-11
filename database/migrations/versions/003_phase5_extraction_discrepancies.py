"""003_phase5_extraction_discrepancies

Revision ID: 003_phase5_extraction_discrepancies
Revises: 002_phase4_auth_audit_review
Create Date: 2026-09-11 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_phase5_extraction_discrepancies'
down_revision: Union[str, None] = '002_phase4_auth_audit_review'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. extraction_results: add structured_fields and confidence_category
    op.add_column('extraction_results', sa.Column('structured_fields', sa.JSON(), nullable=True))
    op.add_column('extraction_results', sa.Column('confidence_category', sa.String(length=20), server_default='HIGH', nullable=False))

    # 2. land_records: add structured extraction fields
    op.add_column('land_records', sa.Column('owner_name', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_land_records_owner_name'), 'land_records', ['owner_name'], unique=False)
    op.add_column('land_records', sa.Column('co_owners', sa.JSON(), nullable=True))
    op.add_column('land_records', sa.Column('patta_number', sa.String(length=50), nullable=True))
    op.add_column('land_records', sa.Column('registration_number', sa.String(length=100), nullable=True))
    op.add_column('land_records', sa.Column('mutation_number', sa.String(length=100), nullable=True))
    op.add_column('land_records', sa.Column('document_date', sa.DateTime(), nullable=True))

    # 3. record_comparisons table
    op.create_table(
        'record_comparisons',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('record_id', sa.Uuid(), nullable=False),
        sa.Column('compared_record_id', sa.Uuid(), nullable=False),
        sa.Column('match_type', sa.String(length=50), server_default='PARCEL_EXACT_MATCH', nullable=False),
        sa.Column('discrepancy_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('highest_severity', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='MATCH_FOUND', nullable=False),
        sa.Column('compared_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['record_id'], ['land_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['compared_record_id'], ['land_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_record_comparisons_record_id'), 'record_comparisons', ['record_id'], unique=False)
    op.create_index(op.f('ix_record_comparisons_compared_record_id'), 'record_comparisons', ['compared_record_id'], unique=False)
    op.create_index('ix_record_comparisons_pair', 'record_comparisons', ['record_id', 'compared_record_id'], unique=False)

    # 4. discrepancies table
    op.create_table(
        'discrepancies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('record_id', sa.Uuid(), nullable=False),
        sa.Column('compared_record_id', sa.Uuid(), nullable=True),
        sa.Column('comparison_id', sa.Uuid(), nullable=True),
        sa.Column('discrepancy_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), server_default='MEDIUM', nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('source_value', sa.Text(), nullable=True),
        sa.Column('conflicting_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='OPEN', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['record_id'], ['land_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['compared_record_id'], ['land_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['comparison_id'], ['record_comparisons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discrepancies_record_id'), 'discrepancies', ['record_id'], unique=False)
    op.create_index(op.f('ix_discrepancies_compared_record_id'), 'discrepancies', ['compared_record_id'], unique=False)
    op.create_index(op.f('ix_discrepancies_comparison_id'), 'discrepancies', ['comparison_id'], unique=False)
    op.create_index(op.f('ix_discrepancies_discrepancy_type'), 'discrepancies', ['discrepancy_type'], unique=False)
    op.create_index(op.f('ix_discrepancies_severity'), 'discrepancies', ['severity'], unique=False)
    op.create_index(op.f('ix_discrepancies_status'), 'discrepancies', ['status'], unique=False)
    op.create_index('ix_discrepancies_record_status', 'discrepancies', ['record_id', 'status'], unique=False)
    op.create_index('ix_discrepancies_type_severity', 'discrepancies', ['discrepancy_type', 'severity'], unique=False)

def downgrade() -> None:
    # Drop discrepancies
    op.drop_index('ix_discrepancies_type_severity', table_name='discrepancies')
    op.drop_index('ix_discrepancies_record_status', table_name='discrepancies')
    op.drop_index(op.f('ix_discrepancies_status'), table_name='discrepancies')
    op.drop_index(op.f('ix_discrepancies_severity'), table_name='discrepancies')
    op.drop_index(op.f('ix_discrepancies_discrepancy_type'), table_name='discrepancies')
    op.drop_index(op.f('ix_discrepancies_comparison_id'), table_name='discrepancies')
    op.drop_index(op.f('ix_discrepancies_compared_record_id'), table_name='discrepancies')
    op.drop_index(op.f('ix_discrepancies_record_id'), table_name='discrepancies')
    op.drop_table('discrepancies')

    # Drop record_comparisons
    op.drop_index('ix_record_comparisons_pair', table_name='record_comparisons')
    op.drop_index(op.f('ix_record_comparisons_compared_record_id'), table_name='record_comparisons')
    op.drop_index(op.f('ix_record_comparisons_record_id'), table_name='record_comparisons')
    op.drop_table('record_comparisons')

    # Drop land_records additions
    op.drop_column('land_records', 'document_date')
    op.drop_column('land_records', 'mutation_number')
    op.drop_column('land_records', 'registration_number')
    op.drop_column('land_records', 'patta_number')
    op.drop_column('land_records', 'co_owners')
    op.drop_index(op.f('ix_land_records_owner_name'), table_name='land_records')
    op.drop_column('land_records', 'owner_name')

    # Drop extraction_results additions
    op.drop_column('extraction_results', 'confidence_category')
    op.drop_column('extraction_results', 'structured_fields')
