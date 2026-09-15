"""Use a supported least-privilege role for new users.

Revision ID: 006_safe_user_role_default
Revises: 005_phase7b_parcel_locations
"""
from alembic import op

revision = "006_safe_user_role_default"
down_revision = "005_phase7b_parcel_locations"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve existing assignments; only correct the default for new rows.
    op.alter_column("users", "role", server_default="VIEWER")


def downgrade():
    op.alter_column("users", "role", server_default="REVENUE_OFFICER")
