import asyncio
import logging
import os
import uuid
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 360
PREVIEW_FPS = 15


async def generate_preview_video(
    video_path: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Generate a 360p preview version of a video segment.
    Used for lazy loading in the browser editor.
    """
    out_dir = output_dir or os.path.join(settings.output_dir, "previews")
    os.makedirs(out_dir, exist_ok=True)
    preview_path = os.path.join(out_dir, f"{uuid.uuid4()}_preview.mp4")

    cmd = [
        settings.ffmpeg_path,
        "-y",
        "-i", video_path,
        "-vf", f"scale={PREVIEW_WIDTH}:{PREVIEW_HEIGHT}:force_original_aspect_ratio=decrease,pad={PREVIEW_WIDTH}:{PREVIEW_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(PREVIEW_FPS),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "64k",
        "-movflags", "+faststart",
        preview_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error(f"FFmpeg preview failed: {stderr.decode()}")
        raise RuntimeError(f"Preview generation failed: {stderr.decode()}")

    logger.info(f"Generated preview: {preview_path}")
    return preview_path


async def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        settings.ffprobe_path,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        return float(stdout.decode().strip())
    return 0.0


async def download_and_generate_preview(
    video_url: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Download a video from URL and generate a 360p preview.
    Used when the video is stored remotely (e.g., S3, CDN).
    """
    out_dir = output_dir or os.path.join(settings.output_dir, "previews")
    os.makedirs(out_dir, exist_ok=True)

    local_path = os.path.join(out_dir, f"{uuid.uuid4()}_original.mp4")
    preview_path = os.path.join(out_dir, f"{uuid.uuid4()}_preview.mp4")

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.get(video_url, follow_redirects=True)
        resp.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(resp.content)

    preview_path = await generate_preview_video(local_path, output_dir=out_dir)

    try:
        os.remove(local_path)
    except Exception:
        pass

    return preview_path


class LazyPreviewService:
    def __init__(self, project_id: str):
        self.project_id = project_id

    async def get_preview_for_segment(self, segment_id: str, video_url: str) -> str:
        """
        Get or generate a 360p preview for a segment.
        Downloads remote video if needed, generates preview.
        """
        preview_dir = os.path.join(settings.output_dir, "previews", self.project_id)
        os.makedirs(preview_dir, exist_ok=True)

        preview_filename = f"{segment_id}_preview.mp4"
        preview_path = os.path.join(preview_dir, preview_filename)

        if os.path.exists(preview_path):
            return preview_path

        if video_url.startswith("http"):
            return await download_and_generate_preview(video_url, output_dir=preview_dir)
        else:
            return await generate_preview_video(video_url, output_dir=preview_dir)

    async def get_viewport_previews(
        self,
        segment_ids: list[str],
        segment_urls: dict[str, str],
    ) -> dict[str, str]:
        """
        Get previews for multiple segments in parallel.
        Used when loading viewport segments in the editor.
        """
        tasks = []
        for seg_id in segment_ids:
            video_url = segment_urls.get(seg_id, "")
            if video_url:
                tasks.append(self.get_preview_for_segment(seg_id, video_url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        previews = {}
        for seg_id, result in zip(segment_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Preview generation failed for segment {seg_id}: {result}")
                previews[seg_id] = None
            else:
                previews[seg_id] = result

        return previews
