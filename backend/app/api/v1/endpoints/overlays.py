from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from app.models.segment import VideoProject, Segment, TextOverlay
from app.schemas.segment import (
    TextOverlayCreate,
    TextOverlayUpdate,
    TextOverlayResponse,
)

router = APIRouter()


async def _verify_segment_access(
    project_id: str, segment_id: str, db: AsyncSession, current_user: User
) -> Segment:
    result = await db.execute(
        select(VideoProject).where(
            VideoProject.id == project_id, VideoProject.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(Segment).where(
            Segment.id == segment_id,
            Segment.project_id == project_id,
            Segment.is_deleted == False,
        )
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    return segment


@router.post(
    "/",
    response_model=TextOverlayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_overlay(
    project_id: str,
    segment_id: str,
    overlay_data: TextOverlayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    segment = await _verify_segment_access(project_id, segment_id, db, current_user)

    overlay = TextOverlay(segment_id=str(segment.id), **overlay_data.model_dump())
    db.add(overlay)
    await db.commit()
    await db.refresh(overlay)
    return overlay


@router.get("/", response_model=list[TextOverlayResponse])
async def list_overlays(
    project_id: str,
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_segment_access(project_id, segment_id, db, current_user)

    result = await db.execute(
        select(TextOverlay).where(TextOverlay.segment_id == segment_id)
    )
    return result.scalars().all()


@router.get("/{overlay_id}", response_model=TextOverlayResponse)
async def get_overlay(
    project_id: str,
    segment_id: str,
    overlay_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_segment_access(project_id, segment_id, db, current_user)

    result = await db.execute(
        select(TextOverlay).where(
            TextOverlay.id == overlay_id,
            TextOverlay.segment_id == segment_id,
        )
    )
    overlay = result.scalar_one_or_none()
    if not overlay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found")
    return overlay


@router.put("/{overlay_id}", response_model=TextOverlayResponse)
async def update_overlay(
    project_id: str,
    segment_id: str,
    overlay_id: str,
    overlay_data: TextOverlayUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_segment_access(project_id, segment_id, db, current_user)

    result = await db.execute(
        select(TextOverlay).where(
            TextOverlay.id == overlay_id,
            TextOverlay.segment_id == segment_id,
        )
    )
    overlay = result.scalar_one_or_none()
    if not overlay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found")

    update_fields = overlay_data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(overlay, key, value)

    await db.commit()
    await db.refresh(overlay)
    return overlay


@router.delete("/{overlay_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_overlay(
    project_id: str,
    segment_id: str,
    overlay_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_segment_access(project_id, segment_id, db, current_user)

    result = await db.execute(
        select(TextOverlay).where(
            TextOverlay.id == overlay_id,
            TextOverlay.segment_id == segment_id,
        )
    )
    overlay = result.scalar_one_or_none()
    if not overlay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found")

    await db.delete(overlay)
    await db.commit()
    return