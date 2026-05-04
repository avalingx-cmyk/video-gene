"""Add content_hash to asset_licenses, can_upload to users

Revision ID: 005_content_hash_upload_gate
Revises: 004_segment_based_architecture
Create Date: 2026-05-02
"""
revision = "005_content_hash_upload_gate"
down_revision = "004_segment_based_architecture"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("asset_licenses", sa.Column("content_hash", sa.String(64), nullable=True))
    op.create_index("ix_asset_licenses_content_hash", "asset_licenses", ["content_hash"])
    op.add_column("users", sa.Column("can_upload", sa.Boolean, server_default="true", nullable=False))


def downgrade():
    op.drop_column("users", "can_upload")
    op.drop_index("ix_asset_licenses_content_hash", table_name="asset_licenses")
    op.drop_column("asset_licenses", "content_hash")
