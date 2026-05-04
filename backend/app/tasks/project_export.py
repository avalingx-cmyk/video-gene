import asyncio
import logging
from app.tasks.celery_app import celery_app
from app.models.segment import VideoProject, ProjectStatus
from app.core.database import async_session
from sqlalchemy import select

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def export_project_task(self, project_id: str, edit_json: dict):
    async def _run():
        async with async_session() as db:
            result = await db.execute(select(VideoProject).where(VideoProject.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                logger.warning(f"Project {project_id} not found")
                return

            project.status = ProjectStatus.exporting
            await db.commit()

            try:
                segments_data = edit_json.get("segments", [])
                text_tracks = edit_json.get("text_tracks", [])
                audio_tracks = edit_json.get("audio_tracks", [])

                segment_ids = [s["id"] for s in segments_data]
                segments_result = await db.execute(
                    select(VideoProject).where(VideoProject.id == project_id)
                )

                from app.models.segment import Segment
                seg_result = await db.execute(
                    select(Segment).where(Segment.project_id == project_id)
                )
                segments = seg_result.scalars().all()
                seg_by_id = {str(s.id): s for s in segments}

                input_segments = []
                transitions = []
                tts_segments = []
                tts_volumes = []

                for seg_data in segments_data:
                    seg = seg_by_id.get(seg_data["id"])
                    if seg and seg.video_local_path:
                        input_segments.append(seg.video_local_path)
                        transitions.append(seg_data.get("transition", "fade"))

                for audio in audio_tracks:
                    if audio["type"] == "tts":
                        for seg in segments:
                            if str(seg.id) == audio.get("segment_id"):
                                if seg.tts_local_path:
                                    tts_segments.append(seg.tts_local_path)
                                    tts_volumes.append(audio.get("volume", 1.0))
                                break

                bgm_url = None
                bgm_volume = 0.2
                for audio in audio_tracks:
                    if audio["type"] == "music":
                        bgm_url = audio.get("url")
                        bgm_volume = audio.get("volume", 0.2)
                        break

                width = edit_json.get("canvas", {}).get("width", 1080)
                height = edit_json.get("canvas", {}).get("height", 1920)

                text_overlays = []
                for track in text_tracks:
                    for seg in segments:
                        if str(seg.id) == track.get("segment_id"):
                            start_time = track.get("start", 0)
                            end_time = track.get("end", seg.duration_seconds or 10)
                            text_overlays.append({
                                "text": track.get("text", ""),
                                "font_size": track.get("style", {}).get("fontSize", 48),
                                "color": track.get("style", {}).get("color", "#FFFFFF"),
                                "stroke_color": track.get("style", {}).get("outlineColor", "#000000"),
                                "stroke_width": track.get("style", {}).get("outlineWidth", 2),
                                "x": track.get("position", {}).get("x", "W/2"),
                                "y": track.get("position", {}).get("y", "H/2"),
                                "start_time": start_time,
                                "end_time": end_time,
                            })
                            break

                from app.services.ffmpeg_service import export_final_video
                from app.core.config import get_settings
                import os
                settings = get_settings()
                output_path = os.path.join(settings.output_dir, f"project_{project_id}.mp4")

                final_path = await export_final_video(
                    input_segments=input_segments,
                    text_overlays=text_overlays,
                    tts_segments=tts_segments,
                    bgm_path=bgm_url,
                    output_path=output_path,
                    transitions=transitions,
                    width=width,
                    height=height,
                )

                project.output_url = final_path
                project.status = ProjectStatus.completed
                await db.commit()
                logger.info(f"Project {project_id} exported to {final_path}")

            except Exception as e:
                logger.error(f"Project {project_id} export failed: {e}")
                project.status = ProjectStatus.failed
                project.error_message = str(e)
                await db.commit()

    asyncio.run(_run())