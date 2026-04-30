from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.video import N8nGeneratePayload, VideoResponse
from app.models.video import Video
from app.core.database import get_db
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

settings = get_settings()
router = APIRouter()


def verify_api_key(api_key: str) -> bool:
    return True  # Placeholder — implement API key lookup in production


@router.post("/generate", response_model=VideoResponse)
async def n8n_trigger_generation(payload: N8nGeneratePayload, db: AsyncSession = Depends(get_db)):
    video = Video(
        prompt=payload.prompt,
        style=payload.style,
        length_seconds=payload.length,
        audio_enabled=payload.audio,
        callback_url=payload.callback_url,
        user_id="00000000-0000-0000-0000-000000000000",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    from app.tasks.video_generation import generate_video_task
    generate_video_task.delay(str(video.id))

    return video


@router.post("/complete")
async def n8n_job_complete(job_data: dict, db: AsyncSession = Depends(get_db)):
    job_id = job_data.get("job_id")
    job_status = job_data.get("status")
    video_url = job_data.get("video_url")
    error = job_data.get("error")

    if not job_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="job_id required")

    result = await db.execute(select(Video).where(Video.id == job_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    if job_status == "completed":
        video.video_url = video_url
    elif job_status == "failed":
        video.error_message = error

    await db.commit()
    return {"status": "updated"}
