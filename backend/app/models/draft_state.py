import uuid
from datetime import datetime, timedelta
from enum import Enum as PyEnum

from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Boolean, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.video import Base
from typing import List, Optional


class PublishStatus(PyEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


class SegmentVersion(Base):
    __tablename__ = "segment_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("segments.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=10.0)
    transition: Mapped[str] = mapped_column(String(50), default="fade")
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    segment: Mapped["Segment"] = relationship("Segment", back_populates="versions")

    __table_args__ = (
        {"schema": None},
    )


class DraftState(Base):
    __tablename__ = "draft_states"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False, index=True, unique=True)
    status: Mapped[PublishStatus] = mapped_column(SAEnum(PublishStatus), default=PublishStatus.draft)
    segment_order: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    project: Mapped["VideoProject"] = relationship("VideoProject", back_populates="draft_state")

    __table_args__ = (
        {"schema": None},
    )


class SegmentRetention(Base):
    __tablename__ = "segment_retention"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("segments.id"), nullable=False, index=True)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    storage_class: Mapped[str] = mapped_column(String(50), default="STANDARD")
    raw_retention_days: Mapped[int] = mapped_column(Integer, default=7)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    segment: Mapped["Segment"] = relationship("Segment", back_populates="retention")

    __table_args__ = (
        {"schema": None},
    )


def _late_bind_relationships():
    from app.models.segment import Segment, VideoProject
    Segment.retention = relationship("SegmentRetention", back_populates="segment", uselist=False)
    Segment.versions = relationship("SegmentVersion", back_populates="segment", cascade="all, delete-orphan")
    VideoProject.draft_state = relationship("DraftState", back_populates="project", uselist=False)
