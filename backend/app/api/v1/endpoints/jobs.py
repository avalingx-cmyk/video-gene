from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.video import JobStatus
from app.models.video import Video, VideoStatus
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Video).where(Video.id == job_id, Video.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobStatus(
        id=str(video.id),
        status=video.status.value,
        error=video.error_message,
        video_url=video.video_url,
    )
