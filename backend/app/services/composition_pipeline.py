import logging
import os
from typing import Optional

from app.services.ffmpeg_service import (
    CompositionResult,
    OverlaySpec,
    SegmentSpec,
    export_final_video,
    concatenate_videos_with_transitions,
    validate_segments,
)

logger = logging.getLogger(__name__)


async def compose_final_video(
    project_id: str,
    segment_ids: list[str],
    output_dir: Optional[str] = None,
    bgm_path: Optional[str] = None,
    fade_in_duration: float = 0.0,
    fade_out_duration: float = 0.5,
) -> Optional[CompositionResult]:
    from app.core.config import get_settings
    from app.core.database import async_session
    from sqlalchemy import select
    from app.models.segment import Segment, SegmentStatus, TextOverlay

    settings = get_settings()
    out_dir = output_dir or settings.output_dir
    os.makedirs(out_dir, exist_ok=True)

    async with async_session() as db:
        result = await db.execute(select(Segment).where(Segment.id.in_(segment_ids)))
        segments = result.scalars().all()
        segments.sort(key=lambda s: s.order_index)

        if not segments:
            logger.warning(f"No segments found for project {project_id}")
            return None

        ready = [s for s in segments if s.status in (
            SegmentStatus.completed,
            SegmentStatus.video_ready,
            SegmentStatus.tts_ready,
        )]
        if not ready:
            logger.warning(f"No ready segments for project {project_id}")
            return None

        segment_specs: list[SegmentSpec] = []
        global_offset = 0.0

        for seg in ready:
            if not seg.video_local_path or not os.path.exists(seg.video_local_path):
                logger.warning(f"Segment {seg.id} video file missing: {seg.video_local_path}")
                continue

            actual_dur = seg.actual_duration_seconds or seg.duration_seconds or 10.0

            overlay_results = await db.execute(
                select(TextOverlay).where(TextOverlay.segment_id == seg.id)
            )
            overlay_dicts = []
            for overlay in overlay_results.scalars().all():
                overlay_dicts.append({
                    "text": overlay.text,
                    "font_size": overlay.font_size,
                    "font_color": overlay.font_color,
                    "stroke_color": overlay.stroke_color,
                    "stroke_width": overlay.stroke_width,
                    "font_family": overlay.font_family,
                    "x": overlay.position_x,
                    "y": overlay.position_y,
                    "anchor": overlay.anchor,
                    "start_time": overlay.start_time,
                    "end_time": overlay.end_time,
                    "animation": overlay.animation,
                })

            segment_transitions = [seg.transition or "fade"] * max(1, len(ready) - 1)

            spec = SegmentSpec(
                video_path=seg.video_local_path,
                duration=actual_dur,
                tts_path=seg.tts_local_path if seg.tts_local_path and os.path.exists(seg.tts_local_path) else None,
                tts_volume=1.0,
                transition=seg.transition or "fade",
                transition_duration=1.0,
                overlays=[OverlaySpec(**o) for o in overlay_dicts],
                fade_in=0.0,
                fade_out=0.0,
            )
            segment_specs.append(spec)

        if not segment_specs:
            logger.warning(f"No valid segments to compose for project {project_id}")
            return None

        output_path = os.path.join(out_dir, f"{project_id}_final.mp4")

        result = await export_final_video(
            segments=segment_specs,
            bgm_path=bgm_path,
            output_path=output_path,
            width=1080,
            height=1920,
            fade_duration=1.0,
            enable_sidechain_ducking=True,
            fade_in_duration=fade_in_duration,
            fade_out_duration=fade_out_duration,
        )

        logger.info(
            f"Composed final video: {output_path} "
            f"({result.segments_composed} segments, "
            f"{result.overlays_applied} overlays, "
            f"{result.audio_tracks} audio tracks, "
            f"{result.final_duration:.1f}s)"
        )
        return result


async def apply_transition(
    video_path: str,
    next_video_path: str,
    transition_type: str = "fade",
    duration: float = 1.0,
    output_path: Optional[str] = None,
) -> Optional[str]:
    from app.core.config import get_settings

    settings = get_settings()
    out_dir = output_path or settings.output_dir
    fallback_path = os.path.join(out_dir, "transitioned.mp4")

    try:
        result = await concatenate_videos_with_transitions(
            [video_path, next_video_path],
            output_path or fallback_path,
            transitions=[transition_type],
            fade_duration=duration,
        )
        return result
    except Exception as e:
        logger.error(f"Transition failed: {e}")
        return None