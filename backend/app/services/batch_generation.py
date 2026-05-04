import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment import Segment, SegmentStatus, VideoProject, ProjectStatus
from app.models.video import User
from app.core.config import get_settings
from app.services.cost_alerts import CostAlert, CostAlertLevel, check_cost_alert, should_stop_for_cost

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CostInfo:
    user_cost: float
    project_cost: float
    user_cap: Optional[float]
    project_cap: Optional[float]

    def can_afford(self, additional_cost: float) -> bool:
        if self.user_cap is not None and (self.user_cost + additional_cost) > self.user_cap:
            return False
        if self.project_cap is not None and (self.project_cost + additional_cost) > self.project_cap:
            return False
        return True

    def remaining_user_budget(self) -> Optional[float]:
        if self.user_cap is None:
            return None
        return max(0, self.user_cap - self.user_cost)

    def remaining_project_budget(self) -> Optional[float]:
        if self.project_cap is None:
            return None
        return max(0, self.project_cap - self.project_cost)


async def get_cost_info(db: AsyncSession, user_id: str, project_id: str) -> CostInfo:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    result = await db.execute(select(VideoProject).where(VideoProject.id == project_id))
    project = result.scalar_one_or_none()

    user_cost = user.total_cost if user else 0.0
    project_cost = project.total_cost if project else 0.0
    user_cap = user.cost_cap if user else None
    project_cap = project.cost_cap if project else None

    if user_cap is None:
        user_cap = settings.default_cost_cap_per_user
    if project_cap is None:
        project_cap = settings.default_cost_cap_per_project

    return CostInfo(
        user_cost=user_cost,
        project_cost=project_cost,
        user_cap=user_cap,
        project_cap=project_cap,
    )


async def check_cost_limit(db: AsyncSession, user_id: str, project_id: str, segment_cost: float) -> bool:
    cost_info = await get_cost_info(db, user_id, project_id)
    return cost_info.can_afford(segment_cost)


async def update_costs(
    db: AsyncSession,
    user_id: str,
    project_id: str,
    segment_cost: float,
) -> None:
    from app.models.video import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.total_cost = (user.total_cost or 0.0) + segment_cost

    result = await db.execute(select(VideoProject).where(VideoProject.id == project_id))
    project = result.scalar_one_or_none()
    if project:
        project.total_cost = (project.total_cost or 0.0) + segment_cost

    await db.commit()


class BatchGenerationService:
    def __init__(self, db: AsyncSession, project_id: str):
        self.db = db
        self.project_id = project_id

    async def get_pending_segments(self, limit: Optional[int] = None):
        stmt = (
            select(Segment)
            .where(
                Segment.project_id == self.project_id,
                Segment.is_deleted == False,
                Segment.status.in_([
                    SegmentStatus.pending,
                    SegmentStatus.failed,
                ])
            )
            .order_by(Segment.order_index)
        )
        if limit:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_segment_by_id(self, segment_id: str) -> Optional[Segment]:
        result = await self.db.execute(
            select(Segment).where(
                Segment.id == segment_id,
                Segment.project_id == self.project_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_segment_status(
        self,
        segment: Segment,
        status: SegmentStatus,
        video_url: Optional[str] = None,
        tts_url: Optional[str] = None,
        error_message: Optional[str] = None,
        cost: Optional[float] = None,
    ) -> None:
        segment.status = status
        if video_url:
            segment.video_url = video_url
        if tts_url:
            segment.tts_url = tts_url
        if error_message:
            segment.error_message = error_message
        if cost is not None:
            segment.cost = cost

        await self.db.commit()
        logger.info(f"Checkpoint: segment {segment.id} status={status.value}, cost={cost}")

    async def get_project(self) -> Optional[VideoProject]:
        result = await self.db.execute(
            select(VideoProject).where(VideoProject.id == self.project_id)
        )
        return result.scalar_one_or_none()

    async def update_project_status(self, status: ProjectStatus, error_message: Optional[str] = None) -> None:
        project = await self.get_project()
        if project:
            project.status = status
            if error_message:
                project.error_message = error_message
            await self.db.commit()

    async def process_segment_video(
        self,
        segment: Segment,
        cost_override: bool = False,
    ) -> tuple[bool, Optional[CostAlert]]:
        from app.services.fal_client import generate_video_segment
        from app.services.video_router import select_provider

        provider = select_provider(segment.duration_seconds, "educational")

        try:
            cost = settings.fal_cost_per_second * segment.duration_seconds

            cost_info = await get_cost_info(self.db, segment.project.user_id, self.project_id)

            stop, alert = should_stop_for_cost(
                user_cost=cost_info.user_cost,
                project_cost=cost_info.project_cost,
                user_cap=cost_info.user_cap,
                project_cap=cost_info.project_cap,
                override=cost_override,
                alert_threshold=settings.cost_alert_threshold,
                hard_stop_threshold=settings.cost_hard_stop_threshold,
            )

            if alert and alert.level != CostAlertLevel.OK:
                logger.warning(f"Cost alert for segment {segment.id}: {alert.message}")

            if stop:
                logger.warning(f"Cost hard stop reached for segment {segment.id}")
                await self.update_segment_status(
                    segment, SegmentStatus.failed, error_message=f"Cost limit reached: {alert.message}"
                )
                return False, alert

            await self.update_segment_status(segment, SegmentStatus.video_generating)

            video_url = await generate_video_segment(
                prompt=segment.video_prompt,
                duration_seconds=segment.duration_seconds,
                aspect_ratio="9:16",
            )

            await self.update_segment_status(
                segment,
                SegmentStatus.video_ready,
                video_url=video_url,
                cost=cost,
            )

            await update_costs(self.db, segment.project.user_id, self.project_id, cost)
            return True, alert

        except Exception as e:
            logger.error(f"Video generation failed for segment {segment.id}: {e}")
            await self.update_segment_status(
                segment,
                SegmentStatus.failed,
                error_message=str(e),
            )
            return False, None

    async def process_segment_tts(self, segment: Segment, cost_override: bool = False) -> tuple[bool, Optional[CostAlert]]:
        from app.services.tts_pipeline import generate_tts_for_segment

        try:
            if not segment.narration_text:
                return True, None

            cost = settings.groq_cost_per_token * len(segment.narration_text.split())

            cost_info = await get_cost_info(self.db, segment.project.user_id, self.project_id)

            stop, alert = should_stop_for_cost(
                user_cost=cost_info.user_cost,
                project_cost=cost_info.project_cost,
                user_cap=cost_info.user_cap,
                project_cap=cost_info.project_cap,
                override=cost_override,
                alert_threshold=settings.cost_alert_threshold,
                hard_stop_threshold=settings.cost_hard_stop_threshold,
            )

            if stop:
                logger.warning(f"Cost hard stop reached for TTS segment {segment.id}")
                return True, alert

            await self.update_segment_status(segment, SegmentStatus.tts_generating)

            result = await generate_tts_for_segment(segment.narration_text)
            if result["status"] != "success":
                raise RuntimeError(result.get("error", "TTS generation failed"))

            tts_local_path = result.get("local_path") or result.get("url")

            await self.update_segment_status(
                segment,
                SegmentStatus.tts_ready,
                tts_url=tts_local_path,
                cost=cost,
            )

            await update_costs(self.db, segment.project.user_id, self.project_id, cost)
            return True, alert

        except Exception as e:
            logger.error(f"TTS generation failed for segment {segment.id}: {e}")
            await self.update_segment_status(
                segment,
                SegmentStatus.failed,
                error_message=str(e),
            )
            return False, None

    async def run_checkpointed_batch(
        self,
        max_segments: Optional[int] = None,
        cost_override: bool = False,
    ) -> dict:
        await self.update_project_status(ProjectStatus.generating)

        segments = await self.get_pending_segments(limit=max_segments)
        if not segments:
            logger.info(f"No pending segments for project {self.project_id}")
            await self.update_project_status(ProjectStatus.published)
            return {"status": "no_pending_segments", "processed": 0}

        batch_size = getattr(settings, 'batch_size', 5)
        processed = 0
        failed = 0
        alerts = []
        batch_num = 0

        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            batch_num += 1
            logger.info(f"Processing batch {batch_num}: {len(batch)} segments")

            for segment in batch:
                video_ok, alert = await self.process_segment_video(segment, cost_override=cost_override)
                if alert and alert.level != CostAlertLevel.OK:
                    alerts.append({"segment_id": str(segment.id), "alert": alert.message})
                if not video_ok:
                    failed += 1
                    continue

                tts_ok, alert = await self.process_segment_tts(segment, cost_override=cost_override)
                if alert and alert.level == CostAlertLevel.HARD_STOP:
                    alerts.append({"segment_id": str(segment.id), "alert": alert.message, "type": "hard_stop"})
                    break
                if not tts_ok:
                    failed += 1
                    continue

                await self.update_segment_status(segment, SegmentStatus.completed)
                processed += 1

            logger.info(f"Batch {batch_num} checkpoint: {processed} processed, {failed} failed, {len(batch) - len([s for s in batch if s.status == SegmentStatus.completed])} remaining in batch")

        all_segments = await self.get_pending_segments()
        if not all_segments:
            await self.update_project_status(ProjectStatus.published)
        else:
            await self.update_project_status(ProjectStatus.generating, error_message=f"{failed} segments failed")

        return {
            "status": "completed",
            "processed": processed,
            "failed": failed,
            "remaining": len(all_segments),
            "alerts": alerts,
            "batches": batch_num,
        }