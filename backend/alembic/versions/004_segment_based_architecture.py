"""Add video_projects, segments, text_overlays tables + user cost columns

Revision ID: 004_segment_based_architecture
Revises: 002_assets_bgm_audit
Create Date: 2026-05-02
"""
revision = "004_segment_based_architecture"
down_revision = "002_assets_bgm_audit"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column("users", sa.Column("cost_cap", sa.Float, nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "total_cost",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
    )

    op.create_table(
        "video_projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("style", sa.String(50), server_default="educational"),
        sa.Column("resolution_width", sa.Integer, server_default="1080"),
        sa.Column("resolution_height", sa.Integer, server_default="1920"),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("output_url", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean, server_default="false"),
        sa.Column("cost_cap", sa.Float, nullable=True),
        sa.Column("total_cost", sa.Float, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "segments",
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
        ),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("narration_text", sa.Text, nullable=True),
        sa.Column("video_prompt", sa.Text, nullable=False),
        sa.Column("duration_seconds", sa.Float, server_default="10.0"),
        sa.Column("transition", sa.String(50), server_default="fade"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("video_url", sa.Text, nullable=True),
        sa.Column("video_local_path", sa.Text, nullable=True),
        sa.Column("actual_duration_seconds", sa.Float, nullable=True),
        sa.Column("tts_url", sa.Text, nullable=True),
        sa.Column("tts_local_path", sa.Text, nullable=True),
        sa.Column("tts_actual_duration", sa.Float, nullable=True),
        sa.Column("thumbnail_path", sa.Text, nullable=True),
        sa.Column("preview_path", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default="false", index=True),
        sa.Column("cost", sa.Float, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "text_overlays",
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
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("font_family", sa.String(100), server_default="Arial"),
        sa.Column("font_size", sa.Integer, server_default="48"),
        sa.Column("font_color", sa.String(7), server_default="#FFFFFF"),
        sa.Column("stroke_color", sa.String(7), server_default="#000000"),
        sa.Column("stroke_width", sa.Integer, server_default="2"),
        sa.Column("position_x", sa.Float, server_default="0.5"),
        sa.Column("position_y", sa.Float, server_default="0.5"),
        sa.Column("anchor", sa.String(20), server_default="center"),
        sa.Column("start_time", sa.Float, server_default="0.0"),
        sa.Column("end_time", sa.Float, server_default="10.0"),
        sa.Column("animation", sa.String(50), server_default="none"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("text_overlays")
    op.drop_table("segments")
    op.drop_table("video_projects")
    op.drop_column("users", "total_cost")
    op.drop_column("users", "cost_cap")
