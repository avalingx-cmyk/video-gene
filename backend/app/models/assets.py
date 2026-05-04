import uuid
from datetime import datetime
from enum import Enum as PyEnum

import sqlalchemy as sa
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Boolean, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.video import Base


class AssetType(PyEnum):
    image = "image"
    video = "video"
    audio = "audio"
    font = "font"
    other = "other"


class LicenseType(PyEnum):
    royalty_free = "royalty_free"
    creative_commons = "creative_commons"
    commercial = "commercial"
    public_domain = "public_domain"
    custom = "custom"


class AssetLicense(Base):
    __tablename__ = "asset_licenses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType), nullable=False)
    asset_url: Mapped[str] = mapped_column(Text, nullable=False)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    license_type: Mapped[LicenseType] = mapped_column(SAEnum(LicenseType), nullable=False)
    license_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=False)
    attribution_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_asset_licenses_type", "asset_type"),
        sa.Index("ix_asset_licenses_license", "license_type"),
        sa.Index("ix_asset_licenses_content_hash", "content_hash"),
    )


class BgmTrack(Base):
    __tablename__ = "bgm_tracks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    artist: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(100), default="ambient")
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood_tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_royalty_free: Mapped[bool] = mapped_column(Boolean, default=True)
    license_type: Mapped[str] = mapped_column(String(100), default="royalty_free")
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=False)
    attribution_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_bgm_tracks_genre", "genre"),
        sa.Index("ix_bgm_tracks_mood", "mood_tags"),
        sa.Index("ix_bgm_tracks_active", "is_active"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        sa.Index("ix_audit_logs_action", "action"),
        sa.Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        sa.Index("ix_audit_logs_created", "created_at"),
    )
