from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()


@router.post("/admin/retention/cleanup")
async def trigger_retention_cleanup(
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the retention cleanup job manually.
    Called by a Celery beat schedule or external cron.
    """
    from app.services.retention_service import cleanup_expired_segments

    count = await cleanup_expired_segments(db)
    return {"cleaned_up": count, "message": f"Marked {count} expired segment(s) for deletion"}


@router.post("/admin/retention/policy/apply")
async def apply_retention_policy():
    """
    Apply the 7-day S3 lifecycle expiration policy to the segments bucket.
    Run once during setup or after bucket changes.
    """
    from app.core.config import get_settings
    from app.services.s3_service import apply_7day_expiration_policy

    settings = get_settings()
    if not settings.s3_bucket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="s3_bucket not configured",
        )

    success = apply_7day_expiration_policy(settings.s3_bucket, prefix="segments/")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply lifecycle policy to S3",
        )

    return {"status": "applied", "bucket": settings.s3_bucket, "policy": "7-day expiration + abort-incomplete-uploads"}


@router.get("/admin/retention/inspect")
async def inspect_retention(prefix: str = "segments/", limit: int = 100):
    """
    Inspect which segment objects are currently in S3 and their expiration status.
    """
    from app.core.config import get_settings
    from app.services.s3_service import list_objects

    settings = get_settings()
    if not settings.s3_bucket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="s3_bucket not configured",
        )

    objects = list_objects(settings.s3_bucket, prefix=prefix, max_keys=limit)
    return {"bucket": settings.s3_bucket, "prefix": prefix, "count": len(objects), "objects": objects}