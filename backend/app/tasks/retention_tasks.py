import logging
from celery import Task
from app.tasks.celery_app import celery_app
from app.core.database import get_async_session
from app.services.retention_service import cleanup_expired_segments

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.retention_tasks.cleanup_expired_segments_task")
def cleanup_expired_segments_task(self: Task) -> dict:
    """
    Celery task to clean up expired segment S3 objects and mark DB records as deleted.
    Runs daily via Celery beat at 02:00 UTC.
    """
    import asyncio

    async def _run():
        session_maker = get_async_session()
        async with session_maker() as db:
            count = await cleanup_expired_segments(db)
            return count

    try:
        count = asyncio.run(_run())
        logger.info(f"Retention cleanup completed: {count} segment(s) cleaned up")
        return {"status": "success", "cleaned_up": count}
    except Exception as exc:
        logger.error(f"Retention cleanup failed: {exc}")
        raise self.retry(exc=exc, countdown=300, max_retries=3)