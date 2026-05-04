from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from app.models.assets import BgmTrack
from app.schemas.assets import BgmTrackCreate, BgmTrackUpdate, BgmTrackResponse

router = APIRouter()


@router.post("/", response_model=BgmTrackResponse, status_code=status.HTTP_201_CREATED)
async def create_bgm_track(
    data: BgmTrackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    track = BgmTrack(**data.model_dump())
    db.add(track)
    await db.commit()
    await db.refresh(track)
    return track


@router.get("/", response_model=list[BgmTrackResponse])
async def list_bgm_tracks(
    genre: Optional[str] = Query(None),
    mood: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    royalty_free_only: bool = Query(True),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = select(BgmTrack).where(BgmTrack.is_active == True)

    if royalty_free_only:
        query = query.where(BgmTrack.is_royalty_free == True)
    if genre:
        query = query.where(BgmTrack.genre == genre)
    if mood:
        query = query.where(BgmTrack.mood_tags.ilike(f"%{mood}%"))
    if search:
        query = query.where(
            or_(
                BgmTrack.title.ilike(f"%{search}%"),
                BgmTrack.artist.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(BgmTrack.title).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{track_id}", response_model=BgmTrackResponse)
async def get_bgm_track(
    track_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BgmTrack).where(BgmTrack.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BGM track not found")
    return track


@router.put("/{track_id}", response_model=BgmTrackResponse)
async def update_bgm_track(
    track_id: str,
    data: BgmTrackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(BgmTrack).where(BgmTrack.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BGM track not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(track, key, value)

    await db.commit()
    await db.refresh(track)
    return track


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bgm_track(
    track_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(BgmTrack).where(BgmTrack.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BGM track not found")

    await db.delete(track)
    await db.commit()
    return


@router.get("/genres/list", response_model=list[str])
async def list_bgm_genres(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BgmTrack.genre).where(BgmTrack.is_active == True).distinct().order_by(BgmTrack.genre)
    )
    return [row[0] for row in result.all()]
