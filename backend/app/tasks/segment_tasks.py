from app.tasks.celery_app import celery_app
from app.models.segment import Segment, SegmentStatus
from app.core.database import async_session
from sqlalchemy import select


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_segment_task(self, segment_id: str):
    """
    Per-segment generation task with validation, auto-retry, and provider fallback.
    1. Fetch segment record
    2. Validate prompt and timing
    3. Generate video with provider fallback chain
    4. Generate TTS voiceover with duration contract enforcement
    5. Validate TTS/video sync; resync or fallback if drift > tolerance
    6. Generate preview thumbnail
    7. Update segment status
    """
    import asyncio

    async def _run():
        from app.services.segment_pipeline import (
            validate_segment,
            generate_segment_with_retry,
            generate_preview_thumbnail,
            validate_tts_video_sync,
            DURATION_TOLERANCE_SECONDS,
            MAX_TTS_RESYNC_ATTEMPTS,
        )
        from app.services.ffmpeg_service import extend_audio_to_duration, measure_audio_sync_drift
        from app.services.tts_pipeline import generate_tts_for_segment

        async with async_session() as db:
            result = await db.execute(select(Segment).where(Segment.id == segment_id))
            segment = result.scalar_one_or_none()
            if not segment:
                return

            segment_data = {
                "video_prompt": segment.video_prompt,
                "duration_seconds": segment.duration_seconds,
                "narration_text": segment.narration_text,
            }

            is_valid, validation_errors = validate_segment(segment_data)
            if not is_valid:
                segment.status = SegmentStatus.failed
                segment.error_message = "; ".join(validation_errors)
                await db.commit()
                return

            segment.status = SegmentStatus.video_generating
            await db.commit()

            video_result = await generate_segment_with_retry(segment_data)

            if video_result["status"] == "failed":
                segment.status = SegmentStatus.failed
                segment.error_message = video_result["errors"][0]
                await db.commit()
                return

            segment.video_url = video_result["video_url"]
            segment.video_local_path = video_result["local_path"]
            segment.actual_duration_seconds = video_result["actual_duration_seconds"]
            segment.status = SegmentStatus.video_ready
            await db.commit()

            if segment.narration_text:
                segment.status = SegmentStatus.tts_generating
                await db.commit()

                target_duration = segment.duration_seconds
                tts_result = await generate_tts_for_segment(
                    text=segment.narration_text,
                    output_dir=None,
                )

                if tts_result["status"] == "success":
                    segment.tts_url = tts_result["url"]
                    segment.tts_local_path = tts_result["local_path"]
                    segment.tts_actual_duration = tts_result["duration_seconds"]
                    segment.tts_expected_duration = target_duration

                    is_synced, drift, msg = validate_tts_video_sync(
                        tts_result["duration_seconds"],
                        video_result["actual_duration_seconds"],
                        target_duration,
                    )
                    segment.tts_duration_drift = drift
                    segment.audio_sync_status = "drift_detected" if not is_synced else "ok"

                    if not is_synced:
                        resync_attempts = 0
                        while resync_attempts < MAX_TTS_RESYNC_ATTEMPTS:
                            resync_attempts += 1
                            padded_path = await extend_audio_to_duration(
                                tts_result["local_path"],
                                target_duration,
                            )
                            if padded_path != tts_result["local_path"]:
                                segment.tts_local_path = padded_path
                                await db.commit()

                            new_drift, new_offset = await measure_audio_sync_drift(
                                segment.video_local_path,
                                padded_path if resync_attempts > 1 else tts_result["local_path"],
                            )
                            if abs(new_offset) < 40:
                                segment.audio_sync_status = "ok"
                                segment.tts_duration_drift = new_drift
                                break
                            resync_attempts += 1

                        if resync_attempts >= MAX_TTS_RESYNC_ATTEMPTS:
                            segment.audio_sync_status = "fallback_triggered"
                            segment.tts_local_path = None
                            segment.error_message = "TTS sync drift exceeded 40ms after retries; falling back to native audio"
                            segment.status = SegmentStatus.failed
                            await db.commit()
                            return

                    segment.status = SegmentStatus.tts_ready
                else:
                    segment.error_message = f"TTS failed: {tts_result['error']}"
                    segment.audio_sync_status = "fallback_triggered"
                    segment.status = SegmentStatus.failed

                await db.commit()

            await db.refresh(segment)

            if segment.video_local_path:
                thumbnail_path = await generate_preview_thumbnail(
                    segment.video_local_path,
                    timestamp=1.0,
                    width=360,
                )
                if thumbnail_path:
                    segment.thumbnail_path = thumbnail_path
                    await db.commit()

    asyncio.run(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def composite_project_task(self, project_id: str, bgm_url: str = None, fade_in_duration: float = 0.0, fade_out_duration: float = 0.5, enable_sidechain_ducking: bool = True, transition_duration: float = 1.0):
    """
    Project-level compositing task.
    1. Validate all segments are ready
    2. Download BGM if URL provided
    3. Concatenate video segments with xfade transitions
    4. Mix audio tracks (TTS + BGM with sidechain ducking)
    5. Burn in text overlays (drawtext + ASS fallback)
    6. Generate final 1080p H.264 AAC faststart MP4
    """
    import asyncio
    import tempfile
    import os

    async def _run():
        from app.models.segment import VideoProject, ProjectStatus, Segment, SegmentStatus
        from app.core.config import get_settings

        settings = get_settings()

        async with async_session() as db:
            result = await db.execute(select(VideoProject).where(VideoProject.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                return

            seg_result = await db.execute(
                select(Segment).where(Segment.project_id == project_id, Segment.is_deleted == False)
            )
            segments = seg_result.scalars().all()

            all_ready = all(s.status == SegmentStatus.completed for s in segments)
            any_failed = any(s.status == SegmentStatus.failed for s in segments)

            if any_failed:
                project.status = ProjectStatus.failed
                project.error_message = "One or more segments failed generation"
                await db.commit()
                return

            if not all_ready:
                project.status = ProjectStatus.generating
                await db.commit()
                return

            bgm_path = None
            if bgm_url:
                import httpx
                tmp_dir = tempfile.mkdtemp(prefix="bgm_")
                bgm_local = os.path.join(tmp_dir, "bgm.mp3")
                try:
                    async with httpx.AsyncClient(timeout=60) as client:
                        resp = await client.get(bgm_url, follow_redirects=True)
                        resp.raise_for_status()
                        with open(bgm_local, "wb") as f:
                            f.write(resp.content)
                        bgm_path = bgm_local
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to download BGM from {bgm_url}: {e}")

            from app.services.composition_pipeline import compose_final_video
            composition_result = await compose_final_video(
                project_id,
                [s.id for s in segments],
                bgm_path=bgm_path,
                fade_in_duration=fade_in_duration,
                fade_out_duration=fade_out_duration,
            )

            if bgm_path:
                try:
                    os.unlink(bgm_path)
                    os.rmdir(os.path.dirname(bgm_path))
                except OSError:
                    pass

            if composition_result:
                project.output_url = composition_result.output_path
                project.status = ProjectStatus.published
            else:
                project.status = ProjectStatus.failed
                project.error_message = "Composition failed"

            await db.commit()

    asyncio.run(_run())