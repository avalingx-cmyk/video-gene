from celery import chain, group

from app.tasks.celery_app import celery_app

celery_app.conf.task_time_limit = 900
celery_app.conf.task_soft_time_limit = 840


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_segment_video_task(self, segment_id: str, cost_override: bool = False):
    """
    Generate video for a single segment.
    Called individually per segment to enable checkpointing.
    """
    import asyncio

    async def _run():
        from app.core.database import async_session
        from app.services.batch_generation import BatchGenerationService
        from sqlalchemy import select
        from app.models.segment import Segment

        async with async_session() as db:
            result = await db.execute(select(Segment).where(Segment.id == segment_id))
            segment = result.scalar_one_or_none()
            if not segment:
                return {"status": "error", "message": f"Segment {segment_id} not found"}

            service = BatchGenerationService(db, segment.project_id)
            success, alert = await service.process_segment_video(segment, cost_override=cost_override)
            return {
                "status": "completed" if success else "failed",
                "segment_id": segment_id,
                "project_id": segment.project_id,
                "alert": alert.message if alert else None,
            }

    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_segment_tts_task(self, segment_id: str, cost_override: bool = False):
    """
    Generate TTS for a single segment.
    Called individually per segment to enable checkpointing.
    """
    import asyncio

    async def _run():
        from app.core.database import async_session
        from app.services.batch_generation import BatchGenerationService
        from sqlalchemy import select
        from app.models.segment import Segment

        async with async_session() as db:
            result = await db.execute(select(Segment).where(Segment.id == segment_id))
            segment = result.scalar_one_or_none()
            if not segment:
                return {"status": "error", "message": f"Segment {segment_id} not found"}

            service = BatchGenerationService(db, segment.project_id)
            success, alert = await service.process_segment_tts(segment, cost_override=cost_override)
            return {
                "status": "completed" if success else "failed",
                "segment_id": segment_id,
                "project_id": segment.project_id,
                "alert": alert.message if alert else None,
            }

    return asyncio.run(_run())


@celery_app.task(bind=True, time_limit=3600, soft_time_limit=3540)
def run_batch_generation_task(self, project_id: str, max_segments: int = None, cost_override: bool = False):
    """
    Run batch generation for a project.
    Processes all pending segments with checkpointing after each segment.
    """
    import asyncio

    async def _run():
        from app.core.database import async_session
        from app.services.batch_generation import BatchGenerationService

        async with async_session() as db:
            service = BatchGenerationService(db, project_id)
            result = await service.run_checkpointed_batch(
                max_segments=max_segments,
                cost_override=cost_override,
            )
            return result

    return asyncio.run(_run())


@celery_app.task(bind=True, time_limit=3600, soft_time_limit=3540)
def run_batch_generation_stream_task(self, project_id: str, segment_ids: list, cost_override: bool = False):
    """
    Run batch generation for specific segments with streaming/checkpointing.
    Processes each segment individually and checkpoints after each one.
    """
    import asyncio

    async def _run():
        from app.core.database import async_session
        from app.services.batch_generation import BatchGenerationService
        from sqlalchemy import select
        from app.models.segment import Segment

        async with async_session() as db:
            service = BatchGenerationService(db, project_id)
            results = []
            alerts = []

            for segment_id in segment_ids:
                result = await db.execute(select(Segment).where(Segment.id == segment_id))
                segment = result.scalar_one_or_none()
                if not segment:
                    results.append({"segment_id": segment_id, "status": "error", "message": "not found"})
                    continue

                video_success, alert = await service.process_segment_video(segment, cost_override=cost_override)
                results.append({
                    "segment_id": segment_id,
                    "step": "video",
                    "status": "completed" if video_success else "failed",
                })
                if alert and alert.level.value != "ok":
                    alerts.append({"segment_id": segment_id, "step": "video", "alert": alert.message})

                if video_success:
                    tts_success, alert = await service.process_segment_tts(segment, cost_override=cost_override)
                    results.append({
                        "segment_id": segment_id,
                        "step": "tts",
                        "status": "completed" if tts_success else "failed",
                    })
                    if alert and alert.level.value == "hard_stop":
                        alerts.append({"segment_id": segment_id, "step": "tts", "alert": alert.message, "type": "hard_stop"})
                        break
                    if tts_success:
                        await service.update_segment_status(segment, segment.status.completed)

            return {"results": results, "alerts": alerts}

    return asyncio.run(_run())
