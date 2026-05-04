from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from app.models.assets import AssetLicense, AssetType, LicenseType
from app.schemas.assets import AssetLicenseCreate, AssetLicenseUpdate, AssetLicenseResponse
from app.services.asset_licensing import check_upload_rights, compute_sha256_from_url, find_asset_by_hash

router = APIRouter()


@router.post("/", response_model=AssetLicenseResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_license(
    data: AssetLicenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_upload_rights),
):
    content_hash = data.content_hash or compute_sha256_from_url(data.asset_url)

    existing = await find_asset_by_hash(content_hash, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset with this content hash already exists",
        )

    asset = AssetLicense(
        user_id=current_user.id,
        asset_type=AssetType(data.asset_type),
        asset_url=data.asset_url,
        asset_name=data.asset_name,
        content_hash=content_hash,
        license_type=LicenseType(data.license_type),
        license_url=data.license_url,
        attribution_required=data.attribution_required,
        attribution_text=data.attribution_text,
        expires_at=data.expires_at,
        notes=data.notes,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/", response_model=list[AssetLicenseResponse])
async def list_asset_licenses(
    asset_type: Optional[str] = Query(None),
    license_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(AssetLicense).where(AssetLicense.user_id == current_user.id)
    if asset_type:
        query = query.where(AssetLicense.asset_type == AssetType(asset_type))
    if license_type:
        query = query.where(AssetLicense.license_type == LicenseType(license_type))
    query = query.order_by(AssetLicense.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{asset_id}", response_model=AssetLicenseResponse)
async def get_asset_license(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AssetLicense).where(
            AssetLicense.id == asset_id,
            AssetLicense.user_id == current_user.id,
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset license not found")
    return asset


@router.put("/{asset_id}", response_model=AssetLicenseResponse)
async def update_asset_license(
    asset_id: str,
    data: AssetLicenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_upload_rights),
):
    result = await db.execute(
        select(AssetLicense).where(
            AssetLicense.id == asset_id,
            AssetLicense.user_id == current_user.id,
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset license not found")

    update_data = data.model_dump(exclude_unset=True)
    if "asset_type" in update_data:
        update_data["asset_type"] = AssetType(update_data["asset_type"])
    if "license_type" in update_data:
        update_data["license_type"] = LicenseType(update_data["license_type"])

    for key, value in update_data.items():
        setattr(asset, key, value)

    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset_license(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_upload_rights),
):
    result = await db.execute(
        select(AssetLicense).where(
            AssetLicense.id == asset_id,
            AssetLicense.user_id == current_user.id,
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset license not found")

    await db.delete(asset)
    await db.commit()
    return


@router.post("/{asset_id}/verify", response_model=AssetLicenseResponse)
async def verify_asset_license(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_upload_rights),
):
    result = await db.execute(
        select(AssetLicense).where(
            AssetLicense.id == asset_id,
            AssetLicense.user_id == current_user.id,
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset license not found")

    asset.verified_at = datetime.utcnow()
    asset.verified_by = str(current_user.id)
    await db.commit()
    await db.refresh(asset)
    return asset
