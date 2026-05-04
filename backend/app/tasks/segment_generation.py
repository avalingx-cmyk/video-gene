import logging
from app.tasks.celery_app import celery_app
from app.models.segment import Segment, SegmentStatus, VideoProject, ProjectStatus
from app.core.database import async_session
from sqlalchemy import select
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_segment_task(self, segment_id: str):
    async def _run():
        async with async_session() as db:
            result = await db.execute(select(Segment).where(Segment.id == segment_id))
            segment = result.scalar_one_or_none()
            if not segment:
                logger.warning(f"Segment {segment_id} not found")
                return

            project_result = await db.execute(
                select(VideoProject).where(VideoProject.id == segment.project_id)
            )
            project = project_result.scalar_one_or_none()

            segment.status = SegmentStatus.video_generating
            await db.commit()

            try:
                video_local = await _generate_video(segment.video_prompt, segment.duration_seconds)
                segment.video_local_path = video_local

                actual_duration = await _probe_duration(video_local)
                segment.actual_duration_seconds = actual_duration

                segment.status = SegmentStatus.tts_generating
                await db.commit()

                if segment.narration_text:
                    tts_local = await _generate_tts(
                        segment.narration_text,
                        segment.id,
                    )
                    segment.tts_local_path = tts_local

                    tts_duration = await _probe_duration(tts_local)
                    segment.tts_actual_duration = tts_duration

                segment.status = SegmentStatus.completed
                await db.commit()
                logger.info(f"Segment {segment_id} completed successfully")

                await _check_project_completion(segment.project_id)

            except Exception as e:
                logger.error(f"Segment {segment_id} failed: {e}")
                segment.status = SegmentStatus.failed
                segment.error_message = str(e)
                await db.commit()

    asyncio.run(_run())


async def _generate_video(video_prompt: str, duration_seconds: float) -> str:
    from app.services.fal_client import generate_video_segment
    return await generate_video_segment(
        prompt=video_prompt,
        duration_seconds=duration_seconds,
        aspect_ratio="9:16",
    )


async def _generate_tts(narration_text: str, segment_id: str) -> str:
    from app.services.tts_service import generate_tts_segment
    result = await generate_tts_segment(
        text=narration_text,
        voice="af_heart",
    )
    if result["status"] != "success" or not result["local_path"]:
        raise RuntimeError(result.get("error", "TTS generation failed"))
    return result["local_path"]


async def _probe_duration(file_path: str) -> float:
    from app.services.ffmpeg_service import probe_duration
    return await probe_duration(file_path)


async def _check_project_completion(project_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(Segment).where(Segment.project_id == project_id)
        )
        segments = result.scalars().all()

        if all(s.status == SegmentStatus.completed for s in segments):
            project_result = await db.execute(
                select(VideoProject).where(VideoProject.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            if project:
                project.status = ProjectStatus.preview_ready
                await db.commit()
                logger.info(f"Project {project_id} all segments complete — preview ready")