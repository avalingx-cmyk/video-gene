"""Add asset_licenses, bgm_tracks, audit_logs tables

Revision ID: 002_assets_bgm_audit
Revises: main
Create Date: 2026-05-02
"""
revision = "002_assets_bgm_audit"
down_revision = "main"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        "asset_licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("asset_url", sa.Text, nullable=False),
        sa.Column("asset_name", sa.String(255), nullable=False),
        sa.Column("license_type", sa.String(50), nullable=False),
        sa.Column("license_url", sa.Text, nullable=True),
        sa.Column("attribution_required", sa.Boolean, server_default="false"),
        sa.Column("attribution_text", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_asset_licenses_type", "asset_licenses", ["asset_type"])
    op.create_index("ix_asset_licenses_license", "asset_licenses", ["license_type"])

    op.create_table(
        "bgm_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("artist", sa.String(255), nullable=False),
        sa.Column("genre", sa.String(100), server_default="ambient"),
        sa.Column("duration_seconds", sa.Float, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("file_path", sa.Text, nullable=True),
        sa.Column("mood_tags", sa.String(500), nullable=True),
        sa.Column("bpm", sa.Integer, nullable=True),
        sa.Column("is_royalty_free", sa.Boolean, server_default="true"),
        sa.Column("license_type", sa.String(100), server_default="royalty_free"),
        sa.Column("attribution_required", sa.Boolean, server_default="false"),
        sa.Column("attribution_text", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bgm_tracks_genre", "bgm_tracks", ["genre"])
    op.create_index("ix_bgm_tracks_mood", "bgm_tracks", ["mood_tags"])
    op.create_index("ix_bgm_tracks_active", "bgm_tracks", ["is_active"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("bgm_tracks")
    op.drop_table("asset_licenses")
