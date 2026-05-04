import hashlib
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from app.models.assets import AssetLicense


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def compute_sha256_from_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


async def check_upload_rights(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.can_upload:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload rights revoked. Contact administrator.",
        )
    return current_user


async def find_asset_by_hash(
    content_hash: str,
    db: AsyncSession,
) -> AssetLicense | None:
    result = await db.execute(
        select(AssetLicense).where(AssetLicense.content_hash == content_hash)
    )
    return result.scalar_one_or_none()
