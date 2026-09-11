"""005_phase7b_parcel_locations

Revision ID: 005_phase7b_parcel_locations
Revises: 004_phase7a_processing_jobs
Create Date: 2026-09-11 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_phase7b_parcel_locations'
down_revision: Union[str, None] = '004_phase7a_processing_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'parcel_locations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('record_id', sa.Uuid(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('boundary_geojson', sa.JSON(), nullable=True),
        sa.Column('coordinate_reference_system', sa.String(length=50), server_default='EPSG:4326', nullable=False),
        sa.Column('geometry_validation_status', sa.String(length=50), server_default='VALID', nullable=False),
        sa.Column('map_source', sa.String(length=100), server_default='CADASTRAL_SURVEY', nullable=False),
        sa.Column('location_confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['record_id'], ['land_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_id', name='uq_parcel_locations_record_id')
    )
    op.create_index(op.f('ix_parcel_locations_record_id'), 'parcel_locations', ['record_id'], unique=True)
    op.create_index(op.f('ix_parcel_locations_latitude'), 'parcel_locations', ['latitude'], unique=False)
    op.create_index(op.f('ix_parcel_locations_longitude'), 'parcel_locations', ['longitude'], unique=False)
    op.create_index('ix_parcel_locations_coords', 'parcel_locations', ['latitude', 'longitude'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_parcel_locations_coords', table_name='parcel_locations')
    op.drop_index(op.f('ix_parcel_locations_longitude'), table_name='parcel_locations')
    op.drop_index(op.f('ix_parcel_locations_latitude'), table_name='parcel_locations')
    op.drop_index(op.f('ix_parcel_locations_record_id'), table_name='parcel_locations')
    op.drop_table('parcel_locations')
