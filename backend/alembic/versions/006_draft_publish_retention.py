"""Add draft_states, segment_versions, segment_retention tables

Revision ID: 006_draft_publish_retention
Revises: 005_content_hash_upload_gate
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006_draft_publish_retention"
down_revision = "005_content_hash_upload_gate"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "segment_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("segments.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("narration_text", sa.Text, nullable=True),
        sa.Column("video_prompt", sa.Text, nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("duration_seconds", sa.Float, server_default="10.0"),
        sa.Column("transition", sa.String(50), server_default="fade"),
        sa.Column("s3_key", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=True),
    )

    op.create_table(
        "draft_states",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("video_projects.id"),
            nullable=False,
            index=True,
            unique=True,
        ),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("segment_order", postgresql.JSON, nullable=True),
        sa.Column(
            "last_modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version_count", sa.Integer, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "segment_retention",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("segments.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("s3_key", sa.Text, nullable=False),
        sa.Column("storage_class", sa.String(50), server_default="STANDARD"),
        sa.Column("raw_retention_days", sa.Integer, server_default="7"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("segment_retention")
    op.drop_table("draft_states")
    op.drop_table("segment_versions")