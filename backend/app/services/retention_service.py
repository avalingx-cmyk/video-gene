import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.draft_state import SegmentRetention, PublishStatus, DraftState

logger = logging.getLogger(__name__)

RETENTION_DAYS = 7


async def cleanup_expired_segments(db: AsyncSession) -> int:
    from app.core.config import get_settings
    from app.services.s3_service import delete_object

    settings = get_settings()
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    result = await db.execute(
        select(SegmentRetention).where(
            SegmentRetention.expires_at <= cutoff,
            SegmentRetention.is_deleted == False,
        )
    )
    expired = result.scalars().all()

    deleted_count = 0
    for retention in expired:
        try:
            if settings.s3_bucket and retention.s3_key:
                delete_object(settings.s3_bucket, retention.s3_key)
            retention.is_deleted = True
            retention.deleted_at = datetime.utcnow()
            deleted_count += 1
            logger.info(
                f"Marked segment {retention.segment_id} S3 key {retention.s3_key} as deleted (expired {retention.expires_at})"
            )
        except Exception as e:
            logger.warning(f"Failed to mark retention {retention.id} as deleted: {e}")

    if deleted_count > 0:
        await db.commit()

    logger.info(f"Retention cleanup: marked {deleted_count} segments as deleted")
    return deleted_count


async def schedule_retention(
    db: AsyncSession,
    segment_id: str,
    s3_key: str,
    storage_class: str = "STANDARD",
    raw_retention_days: int = RETENTION_DAYS,
) -> SegmentRetention:
    expires_at = datetime.utcnow() + timedelta(days=raw_retention_days)
    retention = SegmentRetention(
        segment_id=segment_id,
        s3_key=s3_key,
        storage_class=storage_class,
        raw_retention_days=raw_retention_days,
        expires_at=expires_at,
    )
    db.add(retention)
    await db.commit()
    await db.refresh(retention)
    logger.info(f"Scheduled retention for segment {segment_id}: expires {expires_at}")
    return retention


async def publish_project(db: AsyncSession, project_id: str, user_id: str | None = None) -> DraftState:
    result = await db.execute(
        select(DraftState).where(DraftState.project_id == project_id)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        draft = DraftState(project_id=project_id)
        db.add(draft)

    draft.status = PublishStatus.published
    draft.published_at = datetime.utcnow()
    await db.commit()
    await db.refresh(draft)
    logger.info(f"Published project {project_id}")
    return draft


async def archive_project(db: AsyncSession, project_id: str) -> DraftState:
    result = await db.execute(
        select(DraftState).where(DraftState.project_id == project_id)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        draft = DraftState(project_id=project_id)
        db.add(draft)

    draft.status = PublishStatus.archived
    await db.commit()
    await db.refresh(draft)
    logger.info(f"Archived project {project_id}")
    return draft


async def save_segment_version(
    db: AsyncSession,
    segment,
    created_by: str | None = None,
) -> int:
    from app.models.draft_state import SegmentVersion

    result = await db.execute(
        select(SegmentVersion)
        .where(SegmentVersion.segment_id == segment.id)
        .order_by(SegmentVersion.version_number.desc())
        .limit(1)
    )
    last_version = result.scalar_one_or_none()
    next_version = (last_version.version_number + 1) if last_version else 1

    version = SegmentVersion(
        segment_id=segment.id,
        version_number=next_version,
        title=segment.title,
        narration_text=segment.narration_text,
        video_prompt=segment.video_prompt,
        order_index=segment.order_index,
        duration_seconds=segment.duration_seconds,
        transition=segment.transition,
        created_by=created_by,
    )
    db.add(version)

    draft_result = await db.execute(
        select(DraftState).where(DraftState.project_id == segment.project_id)
    )
    draft = draft_result.scalar_one_or_none()
    if draft:
        draft.version_count += 1
        draft.last_modified_at = datetime.utcnow()

    await db.commit()
    logger.info(f"Saved version {next_version} for segment {segment.id}")
    return next_version


async def get_draft_state(db: AsyncSession, project_id: str) -> DraftState | None:
    result = await db.execute(
        select(DraftState).where(DraftState.project_id == project_id)
    )
    return result.scalar_one_or_none()