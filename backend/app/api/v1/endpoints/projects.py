from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from app.models.segment import VideoProject, Segment
from typing import Optional
from app.schemas.segment import ProjectCreate, ProjectResponse, ProjectUpdate, SegmentCreate, SegmentResponse, SegmentUpdate, PaginatedSegmentsResponse, SegmentReorder, ExportProjectRequest
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = VideoProject(
        user_id=current_user.id,
        title=project_data.title,
        prompt=project_data.prompt,
        style=project_data.style,
        resolution_width=project_data.resolution_width,
        resolution_height=project_data.resolution_height,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(VideoProject)
        .where(VideoProject.user_id == current_user.id)
        .order_by(VideoProject.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
        .options(selectinload(VideoProject.segments))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    update_data = project_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.post("/{project_id}/publish", response_model=ProjectResponse)
async def publish_project_endpoint(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.segment import ProjectStatus
    from app.services.retention_service import publish_project as publish_project_service

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.status == ProjectStatus.published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project already published")

    project.status = ProjectStatus.published
    project.published_at = datetime.utcnow()
    await db.commit()

    await publish_project_service(db, project_id, str(current_user.id))
    await db.refresh(project)
    return project


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project_endpoint(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.segment import ProjectStatus
    from app.services.retention_service import archive_project as archive_project_service

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.status == ProjectStatus.archived:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project already archived")

    project.status = ProjectStatus.archived
    project.is_archived = True
    await db.commit()

    await archive_project_service(db, project_id)
    await db.refresh(project)
    return project


@router.post("/{project_id}/segments/", response_model=SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    project_id: str,
    segment_data: SegmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select, func

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get the current max order_index for the project
    max_order_index = await db.scalar(
        select(func.max(Segment.order_index)).where(Segment.project_id == project_id)
    )
    if max_order_index is None:
        max_order_index = -1

    segment = Segment(
        project_id=project_id,
        order_index=max_order_index + 1,
        **segment_data.dict(),
    )
    db.add(segment)
    await db.commit()
    await db.refresh(segment)
    return segment


@router.get("/{project_id}/segments/", response_model=PaginatedSegmentsResponse)
async def list_segments(
    project_id: str,
    offset: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select, func

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    count_result = await db.execute(
        select(func.count(Segment.id)).where(Segment.project_id == project_id, Segment.is_deleted == False)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Segment)
        .where(Segment.project_id == project_id, Segment.is_deleted == False)
        .order_by(Segment.order_index)
        .offset(offset)
        .limit(limit)
    )
    segments = result.scalars().all()

    return {
        "segments": segments,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + limit) < total,
    }


@router.put("/{project_id}/segments/{segment_id}", response_model=SegmentResponse)
async def update_segment(
    project_id: str,
    segment_id: str,
    segment_data: SegmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(Segment).where(Segment.id == segment_id, Segment.project_id == project_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    update_data = segment_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(segment, key, value)

    await db.commit()
    await db.refresh(segment)
    return segment


@router.delete("/{project_id}/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    project_id: str,
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(Segment).where(Segment.id == segment_id, Segment.project_id == project_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    segment.is_deleted = True
    await db.commit()
    return


@router.post("/{project_id}/segments/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_segments(
    project_id: str,
    reorder_data: SegmentReorder,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(Segment).where(Segment.project_id == project_id, Segment.is_deleted == False)
    )
    segments = result.scalars().all()
    segment_map = {str(s.id): s for s in segments}

    if len(reorder_data.segment_ids) != len(segments):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid segment list")

    for i, segment_id in enumerate(reorder_data.segment_ids):
        segment = segment_map.get(segment_id)
        if not segment:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid segment id: {segment_id}")
        segment.order_index = i

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not reorder segments")

    return


@router.post("/{project_id}/batch-generate")
async def start_batch_generation(
    project_id: str,
    max_segments: int = None,
    cost_override: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.tasks.batch_generation import run_batch_generation_task

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    task = run_batch_generation_task.delay(str(project_id), max_segments=max_segments, cost_override=cost_override)

    return {"task_id": task.id, "project_id": str(project_id), "status": "queued", "cost_override": cost_override}


@router.get("/{project_id}/batch-status/{task_id}")
async def get_batch_status(
    project_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.tasks.batch_generation import run_batch_generation_task

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    task = run_batch_generation_task.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.state,
        "result": task.result if task.ready() else None,
    }


@router.get("/{project_id}/generation-progress")
async def get_generation_progress(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select, func
    from app.models.segment import SegmentStatus

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    status_counts = {}
    for status in SegmentStatus:
        count_result = await db.execute(
            select(func.count(Segment.id)).where(
                Segment.project_id == project_id,
                Segment.is_deleted == False,
                Segment.status == status,
            )
        )
        status_counts[status.value] = count_result.scalar() or 0

    total_result = await db.execute(
        select(func.count(Segment.id)).where(
            Segment.project_id == project_id,
            Segment.is_deleted == False,
        )
    )
    total = total_result.scalar() or 0

    completed = status_counts.get("completed", 0)
    failed = status_counts.get("failed", 0)
    pending = status_counts.get("pending", 0)
    generating = total - completed - failed - pending

    return {
        "project_id": str(project_id),
        "status": project.status.value,
        "total_segments": total,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "generating": generating,
        "progress_percent": (completed / total * 100) if total > 0 else 0,
        "status_breakdown": status_counts,
    }


@router.post("/{project_id}/preview/{segment_id}")
async def get_segment_preview(
    project_id: str,
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.services.preview_service import LazyPreviewService

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(Segment).where(Segment.id == segment_id, Segment.project_id == project_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")

    if not segment.video_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not ready")

    service = LazyPreviewService(project_id)
    preview_path = await service.get_preview_for_segment(segment_id, segment.video_url)

    return {"preview_url": preview_path, "segment_id": segment_id}


@router.post("/{project_id}/previews")
async def get_viewport_previews(
    project_id: str,
    segment_ids: list[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.services.preview_service import LazyPreviewService

    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(Segment).where(
            Segment.project_id == project_id,
            Segment.id.in_(segment_ids),
        )
    )
    segments = result.scalars().all()
    segment_map = {str(s.id): s for s in segments}

    missing = set(segment_ids) - set(segment_map.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segments not found: {missing}",
        )

    segment_urls = {str(s.id): s.video_url for s in segments if s.video_url}

    service = LazyPreviewService(project_id)
    previews = await service.get_viewport_previews(list(segment_ids), segment_urls)

    return {"previews": previews, "project_id": str(project_id)}


@router.post("/{project_id}/export")
async def export_project(
    project_id: str,
    export_request: Optional[ExportProjectRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    result = await db.execute(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    bgm_url = None
    if export_request:
        bgm_url = export_request.background_music_url

    from app.tasks.segment_tasks import composite_project_task
    task = composite_project_task.delay(str(project_id), bgm_url=bgm_url)

    return {"project_id": str(project_id), "task_id": task.id, "status": "export_queued"}


@router.post("/{project_id}/compose")
async def compose_project(
    project_id: str,
    export_request: ExportProjectRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger FFmpeg composition: concatenate video segments with xfade transitions,
    burn in text overlays, and mix TTS + BGM with optional sidechain ducking.
    """
    from sqlalchemy import select
    from app.models.segment import Segment, SegmentStatus, ProjectStatus

    result = await db.execute(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    seg_result = await db.execute(
        select(Segment).where(Segment.project_id == project_id, Segment.is_deleted == False)
    )
    segments = seg_result.scalars().all()

    ready_segments = [
        s for s in segments
        if s.status in (SegmentStatus.completed, SegmentStatus.video_ready, SegmentStatus.tts_ready)
    ]
    if not ready_segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No segments ready for composition",
        )

    bgm_url = None
    fade_in = 0.0
    fade_out = 0.5
    enable_ducking = True
    trans_dur = 1.0
    if export_request:
        bgm_url = export_request.background_music_url
        fade_in = export_request.fade_in_duration
        fade_out = export_request.fade_out_duration
        enable_ducking = export_request.enable_sidechain_ducking
        trans_dur = export_request.transition_duration

    from app.tasks.segment_tasks import composite_project_task
    task = composite_project_task.delay(
        str(project_id),
        bgm_url=bgm_url,
        fade_in_duration=fade_in,
        fade_out_duration=fade_out,
        enable_sidechain_ducking=enable_ducking,
        transition_duration=trans_dur,
    )

    return {
        "task_id": task.id,
        "project_id": str(project_id),
        "status": "composition_queued",
        "ready_segments": len(ready_segments),
    }


@router.get("/{project_id}/compose-status/{task_id}")
async def get_compose_status(
    project_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll Celery status for a composition task."""
    from sqlalchemy import select
    from app.tasks.segment_tasks import composite_project_task

    result = await db.execute(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    task = composite_project_task.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.state,
        "result": task.result if task.ready() else None,
    }
