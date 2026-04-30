from app.tasks.celery_app import celery_app
from app.models.video import VideoStatus


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def generate_video_task(self, video_id: str):
    """
    Main video generation task.
    1. Fetch video record from DB
    2. Run content filter
    3. Enhance prompt
    4. Select provider via router
    5. Submit to external API
    6. Poll for completion
    7. Download video, process with FFmpeg
    8. Add audio if enabled
    9. Upload to storage
    10. Update DB and trigger callback
    """
    # TODO: Implement full pipeline
    # This is a scaffold — each step will be implemented as services

    from app.core.database import async_session
    from sqlalchemy import select
    import httpx

    async def _run():
        async with async_session() as db:
            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return

            video.status = VideoStatus.processing
            await db.commit()

            # Step 1: Content filter
            from app.services.content_filter import filter_content
            is_safe, reason = filter_content(video.prompt)
            if not is_safe:
                video.status = VideoStatus.failed
                video.error_message = f"Content blocked: {reason}"
                await db.commit()
                return

            # Step 2: Prompt enhancement
            from app.services.prompt_enhancer import enhance_prompt
            enhanced_prompt = enhance_prompt(video.prompt, video.style)

            # Step 3: Provider selection and video generation
            from app.services.video_router import generate_with_router
            try:
                video_url = await generate_with_router(
                    prompt=enhanced_prompt,
                    style=video.style,
                    length_seconds=video.length_seconds,
                )
                video.video_url = video_url
                video.status = VideoStatus.completed
            except Exception as e:
                video.status = VideoStatus.failed
                video.error_message = str(e)

            await db.commit()

    # Run async code in sync Celery task
    import asyncio
    asyncio.run(_run())
