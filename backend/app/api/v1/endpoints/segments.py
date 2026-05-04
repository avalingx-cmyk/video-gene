from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from app.models.segment import Segment, SegmentStatus
from app.tasks.segment_tasks import generate_segment_task

router = APIRouter()


@router.get("/segments/{segment_id}/versions")
async def list_segment_versions(
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all version history for a segment (for reorder/retitle)."""
    from app.models.draft_state import SegmentVersion

    result = await db.execute(select(Segment).where(Segment.id == segment_id))
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    if segment.project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    versions_result = await db.execute(
        select(SegmentVersion)
        .where(SegmentVersion.segment_id == segment_id)
        .order_by(SegmentVersion.version_number.desc())
    )
    versions = versions_result.scalars().all()

    return {
        "segment_id": segment_id,
        "versions": [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "title": v.title,
                "narration_text": v.narration_text,
                "video_prompt": v.video_prompt,
                "order_index": v.order_index,
                "duration_seconds": v.duration_seconds,
                "transition": v.transition,
                "s3_key": v.s3_key,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "created_by": v.created_by,
            }
            for v in versions
        ],
    }


@router.post("/segments/{segment_id}/versions/{version_number}/restore")
async def restore_segment_version(
    segment_id: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore a segment to a previous version (reorder/retitle)."""
    from app.models.draft_state import SegmentVersion

    result = await db.execute(select(Segment).where(Segment.id == segment_id))
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    if segment.project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    version_result = await db.execute(
        select(SegmentVersion).where(
            SegmentVersion.segment_id == segment_id,
            SegmentVersion.version_number == version_number,
        )
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    segment.title = version.title
    segment.narration_text = version.narration_text
    segment.video_prompt = version.video_prompt
    segment.order_index = version.order_index
    segment.duration_seconds = version.duration_seconds
    segment.transition = version.transition

    await db.commit()
    return {"segment_id": segment_id, "restored_to_version": version_number}


@router.post("/segments/{segment_id}/versions")
async def create_segment_version(
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually snapshot current segment state as a new version."""
    from app.services.retention_service import save_segment_version

    result = await db.execute(select(Segment).where(Segment.id == segment_id))
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    if segment.project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    next_version = await save_segment_version(db, segment, str(current_user.id))
    return {"segment_id": segment_id, "version_number": next_version}


@router.post("/segments/{segment_id}/regenerate")
async def regenerate_segment(
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-roll a single segment without regenerating other segments.
    Resets segment to pending and queues new generation task.
    """
    result = await db.execute(
        select(Segment).where(Segment.id == segment_id)
    )
    segment = result.scalar_one_or_none()

    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    if segment.project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if segment.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Segment is deleted")

    segment.status = SegmentStatus.pending
    segment.video_url = None
    segment.video_local_path = None
    segment.actual_duration_seconds = None
    segment.tts_url = None
    segment.tts_local_path = None
    segment.tts_actual_duration = None
    segment.thumbnail_path = None
    segment.preview_path = None
    segment.error_message = None
    await db.commit()

    generate_segment_task.delay(str(segment_id))

    return {"segment_id": str(segment_id), "status": "queued"}


@router.get("/segments/{segment_id}/status")
async def get_segment_status(
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current status of a segment including preview URLs."""
    result = await db.execute(
        select(Segment).where(Segment.id == segment_id)
    )
    segment = result.scalar_one_or_none()

    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    if segment.project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return {
        "id": str(segment.id),
        "status": segment.status.value,
        "video_url": segment.video_url,
        "video_local_path": segment.video_local_path,
        "thumbnail_path": segment.thumbnail_path,
        "preview_path": segment.preview_path,
        "actual_duration_seconds": segment.actual_duration_seconds,
        "tts_url": segment.tts_url,
        "tts_local_path": segment.tts_local_path,
        "tts_actual_duration": segment.tts_actual_duration,
        "error_message": segment.error_message,
    }