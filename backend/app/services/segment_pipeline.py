import asyncio
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

MAX_DURATION_SECONDS = 15
MIN_DURATION_SECONDS = 5
MAX_RETRIES = 3
DURATION_TOLERANCE_SECONDS = 0.5
TTS_DURATION_TOLERANCE_SECONDS = 0.5
MAX_TTS_RESYNC_ATTEMPTS = 2

VIDEO_PROHIBITED_PATTERNS = [
    "title", "subtitle", "caption", "brand", "logo",
    "words", "letters", "sign", "display", "written", "reading",
]

TEXT_IN_VIDEO_ERROR = "Prompt contains text/brand content — video segments must not include text overlays"


def validate_segment_prompt(prompt: str) -> tuple[bool, str]:
    """Validate that prompt contains no text/brand content for video generation."""
    prompt_lower = prompt.lower()
    for pattern in VIDEO_PROHIBITED_PATTERNS:
        if pattern in prompt_lower:
            return False, f"Prompt contains prohibited text pattern '{pattern}': video segments must be clean footage only"
    return True, ""


def validate_segment_duration(duration_seconds: float) -> tuple[bool, str]:
    """Validate segment duration is within acceptable range."""
    if duration_seconds < MIN_DURATION_SECONDS:
        return False, f"Segment duration {duration_seconds}s is below minimum {MIN_DURATION_SECONDS}s"
    if duration_seconds > MAX_DURATION_SECONDS:
        return False, f"Segment duration {duration_seconds}s exceeds maximum {MAX_DURATION_SECONDS}s"
    return True, ""


def validate_narration_timing(narration_text: str, duration_seconds: float) -> tuple[bool, str]:
    """Validate narration timing is consistent with segment duration."""
    words_per_minute = 150
    estimated_words = len(narration_text.split())
    estimated_duration = (estimated_words / words_per_minute) * 60
    if estimated_duration > duration_seconds * 1.5:
        return False, f"Narration estimated at {estimated_duration:.0f}s exceeds segment duration {duration_seconds}s by >50%"
    return True, ""


def validate_tts_video_sync(
    tts_actual_duration: float,
    video_actual_duration: float,
    target_duration: float,
) -> tuple[bool, float, str]:
    """
    Validate that TTS duration matches the video segment duration within tolerance.
    Returns (is_synced, drift_seconds, message).
    """
    video_drift = abs(video_actual_duration - target_duration)
    tts_drift = abs(tts_actual_duration - target_duration)

    if tts_drift <= TTS_DURATION_TOLERANCE_SECONDS and video_drift <= DURATION_TOLERANCE_SECONDS:
        return True, tts_drift, "ok"

    drift = tts_actual_duration - video_actual_duration
    return False, drift, f"TTS drift {drift:+.2f}s (tts={tts_actual_duration:.2f}s, video={video_actual_duration:.2f}s, target={target_duration:.2f}s)"


def compute_tts_padding_needed(
    tts_duration: float,
    target_duration: float,
) -> float:
    """Compute silence padding (in seconds) needed to stretch TTS to target duration."""
    return max(0.0, target_duration - tts_duration)


def validate_segment(segment_data: dict) -> tuple[bool, list[str]]:
    """Full segment validation returning all errors."""
    errors = []

    if "video_prompt" in segment_data:
        ok, msg = validate_segment_prompt(segment_data["video_prompt"])
        if not ok:
            errors.append(msg)

    if "duration_seconds" in segment_data:
        ok, msg = validate_segment_duration(segment_data["duration_seconds"])
        if not ok:
            errors.append(msg)

    if "narration_text" in segment_data and segment_data["narration_text"]:
        ok, msg = validate_narration_timing(
            segment_data["narration_text"],
            segment_data.get("duration_seconds", 10.0)
        )
        if not ok:
            errors.append(msg)

    return len(errors) == 0, errors


async def generate_segment_with_retry(
    segment_data: dict,
    output_dir: str | None = None,
) -> dict:
    """
    Generate a video segment with automatic retry and provider fallback.
    Returns dict with video_url, local_path, provider, and status.
    """
    import httpx
    from app.services.video_router import PROVIDER_PRIORITY, generate_with_provider
    from app.core.config import get_settings

    settings = get_settings()
    prompt = segment_data["video_prompt"]
    duration = segment_data.get("duration_seconds", 10.0)
    out_dir = output_dir or settings.output_dir

    last_error = None

    for attempt in range(MAX_RETRIES):
        for provider in PROVIDER_PRIORITY:
            try:
                logger.info(f"Attempt {attempt + 1}: trying provider {provider.value}")
                video_url = await generate_with_provider(provider, prompt, duration)

                local_path = await _download_video(video_url, out_dir)

                actual_duration = await _get_video_duration(local_path)

                return {
                    "status": "success",
                    "video_url": video_url,
                    "local_path": local_path,
                    "provider": provider.value,
                    "actual_duration_seconds": actual_duration,
                    "errors": [],
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Provider {provider.value} failed on attempt {attempt + 1}: {last_error}")
                continue

    return {
        "status": "failed",
        "video_url": None,
        "local_path": None,
        "provider": None,
        "actual_duration_seconds": None,
        "errors": [f"All providers failed after {MAX_RETRIES} retries. Last error: {last_error}"],
    }


async def _download_video(url: str, output_dir: str) -> str:
    """Download video from URL to local path."""
    import httpx
    os.makedirs(output_dir, exist_ok=True)
    local_path = os.path.join(output_dir, f"{uuid.uuid4()}.mp4")

    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)

    logger.info(f"Downloaded video to {local_path} ({len(resp.content)} bytes)")
    return local_path


async def _get_video_duration(local_path: str) -> float:
    """Get actual video duration using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            local_path
        ]
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0:
            return float(stdout.decode().strip())
    except Exception as e:
        logger.warning(f"Could not determine video duration: {e}")
    return 0.0


async def generate_preview_thumbnail(
    video_path: str,
    output_dir: str | None = None,
    timestamp: float = 0.0,
    width: int = 360,
) -> str:
    """Generate a low-res preview thumbnail from video at given timestamp."""
    from app.core.config import get_settings
    settings = get_settings()
    out_dir = output_dir or settings.output_dir
    os.makedirs(out_dir, exist_ok=True)
    thumbnail_path = os.path.join(out_dir, f"{uuid.uuid4()}_thumb.jpg")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-vf", f"scale={width}:-1",
        thumbnail_path,
    ]

    try:
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0 and os.path.exists(thumbnail_path):
            logger.info(f"Generated thumbnail: {thumbnail_path}")
            return thumbnail_path
        else:
            logger.warning(f"Thumbnail generation failed: {stderr.decode()}")
    except Exception as e:
        logger.warning(f"Could not generate thumbnail: {e}")

    return ""


async def generate_preview_video(
    video_path: str,
    output_dir: str | None = None,
    width: int = 360,
) -> str:
    """Generate a low-res preview video (360p) for fast preview."""
    from app.core.config import get_settings
    settings = get_settings()
    out_dir = output_dir or settings.output_dir
    os.makedirs(out_dir, exist_ok=True)
    preview_path = os.path.join(out_dir, f"{uuid.uuid4()}_preview.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"scale={width}:-1",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "64k",
        preview_path,
    ]

    try:
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0 and os.path.exists(preview_path):
            logger.info(f"Generated preview video: {preview_path}")
            return preview_path
        else:
            logger.warning(f"Preview video generation failed: {stderr.decode()}")
    except Exception as e:
        logger.warning(f"Could not generate preview video: {e}")

    return ""