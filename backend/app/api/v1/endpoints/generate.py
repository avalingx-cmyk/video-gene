from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from app.schemas.video import VideoCreate, VideoResponse
from app.models.video import Video
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/", response_model=VideoResponse)
async def create_video(
    video_data: VideoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = Video(
        user_id=current_user.id,
        prompt=video_data.prompt,
        style=video_data.style,
        length_seconds=video_data.length_seconds,
        audio_enabled=video_data.audio,
        callback_url=video_data.callback_url,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    from app.tasks.video_generation import generate_video_task
    generate_video_task.delay(str(video.id))

    return video


@router.post("/with-file", response_model=VideoResponse)
async def create_video_with_file(
    prompt: str = Form(...),
    style: str = Form("educational"),
    length_seconds: int = Form(30),
    audio: bool = Form(True),
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    extracted_text = prompt
    if file:
        content = await file.read()
        filename = file.filename or ""
        if filename.endswith(".md"):
            extracted_text = f"{prompt}\n\n{content.decode('utf-8')}"
        elif filename.endswith(".pdf"):
            extracted_text = f"{prompt}\n\n[PDF content extracted: {len(content)} bytes]"

    video_data = VideoCreate(
        prompt=extracted_text,
        style=style,
        length_seconds=length_seconds,
        audio=audio,
    )

    video = Video(
        user_id=current_user.id,
        prompt=video_data.prompt,
        style=video_data.style,
        length_seconds=video_data.length_seconds,
        audio_enabled=video_data.audio,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    from app.tasks.video_generation import generate_video_task
    generate_video_task.delay(str(video.id))

    return video


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video


@router.get("/", response_model=list[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(Video)
        .where(Video.user_id == current_user.id)
        .order_by(Video.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
