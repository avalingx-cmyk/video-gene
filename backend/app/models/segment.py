import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Boolean, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.video import Base
from typing import List


class ProjectStatus(PyEnum):
    draft = "draft"
    generating = "generating"
    published = "published"
    archived = "archived"
    failed = "failed"


class SegmentStatus(PyEnum):
    pending = "pending"
    script_ready = "script_ready"
    video_generating = "video_generating"
    video_ready = "video_ready"
    tts_generating = "tts_generating"
    tts_ready = "tts_ready"
    tts_resync_needed = "tts_resync_needed"
    compositing = "compositing"
    completed = "completed"
    failed = "failed"


class AudioSyncStatus(PyEnum):
    ok = "ok"
    drift_detected = "drift_detected"
    fallback_triggered = "fallback_triggered"
    untested = "untested"


class VideoProject(Base):
    __tablename__ = "video_projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[str] = mapped_column(String(50), default="educational")
    resolution_width: Mapped[int] = mapped_column(Integer, default=1080)
    resolution_height: Mapped[int] = mapped_column(Integer, default=1920)
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus), default=ProjectStatus.draft)
    output_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    segments: Mapped[List["Segment"]] = relationship("Segment", back_populates="project", cascade="all, delete-orphan")


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=10.0)
    transition: Mapped[str] = mapped_column(String(50), default="fade")
    status: Mapped[SegmentStatus] = mapped_column(SAEnum(SegmentStatus), default=SegmentStatus.pending)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    tts_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tts_local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    tts_actual_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    tts_expected_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    tts_duration_drift: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["VideoProject"] = relationship("VideoProject", back_populates="segments")
    text_overlays: Mapped[List["TextOverlay"]] = relationship("TextOverlay", back_populates="segment", cascade="all, delete-orphan")


class TextOverlay(Base):
    __tablename__ = "text_overlays"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("segments.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    font_family: Mapped[str] = mapped_column(String(100), default="Arial")
    font_size: Mapped[int] = mapped_column(Integer, default=48)
    font_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    stroke_color: Mapped[str] = mapped_column(String(7), default="#000000")
    stroke_width: Mapped[int] = mapped_column(Integer, default=2)
    position_x: Mapped[float] = mapped_column(Float, default=0.5)
    position_y: Mapped[float] = mapped_column(Float, default=0.5)
    anchor: Mapped[str] = mapped_column(String(20), default="center")
    start_time: Mapped[float] = mapped_column(Float, default=0.0)
    end_time: Mapped[float] = mapped_column(Float, default=10.0)
    animation: Mapped[str] = mapped_column(String(50), default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    segment: Mapped["Segment"] = relationship("Segment", back_populates="text_overlays")