"""001_phase2_core_domain

Revision ID: 001_phase2_core_domain
Revises: 
Create Date: 2026-09-11 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_phase2_core_domain'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='REVENUE_OFFICER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('doc_type', sa.String(length=50), nullable=False, server_default='JAMABANDI'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='UPLOADED'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)

    # 3. land_records table
    op.create_table(
        'land_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('tehsil', sa.String(length=100), nullable=False),
        sa.Column('village', sa.String(length=100), nullable=False),
        sa.Column('khasra_number', sa.String(length=50), nullable=False),
        sa.Column('khata_number', sa.String(length=50), nullable=False),
        sa.Column('area_in_hectares', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('land_classification', sa.String(length=100), nullable=True, server_default='Agricultural'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='EXTRACTED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_land_records_document_id'), 'land_records', ['document_id'], unique=False)
    op.create_index(op.f('ix_land_records_status'), 'land_records', ['status'], unique=False)
    op.create_index('ix_land_records_location', 'land_records', ['state', 'district', 'tehsil', 'village'], unique=False)
    op.create_index('ix_land_records_khasra_khata', 'land_records', ['khasra_number', 'khata_number'], unique=False)

    # 4. extraction_results table
    op.create_table(
        'extraction_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='MOCK_OCR_V1'),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('extracted_fields', sa.JSON(), nullable=False),
        sa.Column('field_confidences', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='SUCCESS'),
        sa.Column('extracted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extraction_results_document_id'), 'extraction_results', ['document_id'], unique=False)

    # 5. validation_results table
    op.create_table(
        'validation_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('record_id', sa.Uuid(), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('rule_results', sa.JSON(), nullable=False),
        sa.Column('discrepancy_summary', sa.Text(), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['record_id'], ['land_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validation_results_record_id'), 'validation_results', ['record_id'], unique=False)


def downgrade() -> None:
    op.drop_table('validation_results')
    op.drop_table('extraction_results')
    op.drop_table('land_records')
    op.drop_table('documents')
    op.drop_table('users')
