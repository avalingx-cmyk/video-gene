import asyncio
import logging
import os
import uuid
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
SETTINGS = get_settings()

SUNO_API_BASE = "https://api.suno.ai"


async def generate_music(
    prompt: str,
    duration: int = 30,
    instrumental: bool = True,
    output_dir: str = None,
) -> dict:
    """
    Generate music using Suno AI.
    Returns dict with status, url, local_path, duration_seconds, and error.
    """
    out_dir = output_dir or SETTINGS.output_dir
    os.makedirs(out_dir, exist_ok=True)
    local_path = os.path.join(out_dir, f"{uuid.uuid4()}.mp3")

    api_key = SETTINGS.suno_api_key
    if not api_key:
        return {
            "status": "failed",
            "error": "SUNO_API_KEY not configured",
            "url": None,
            "local_path": None,
            "duration_seconds": None,
        }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": prompt,
                "duration": duration,
                "instrumental": instrumental,
                "format": "mp3",
            }
            resp = await client.post(
                f"{SUNO_API_BASE}/generate",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            job_id = data.get("job_id")
            if not job_id:
                return {
                    "status": "failed",
                    "error": "No job_id in Suno response",
                    "url": None,
                    "local_path": None,
                    "duration_seconds": None,
                }

            result = await _poll_suno_job(client, headers, job_id, max_attempts=30)

            if result["status"] == "success":
                audio_url = result.get("audio_url")
                if audio_url:
                    await _download_audio(client, audio_url, local_path)
                    duration = await _get_audio_duration(local_path)
                    return {
                        "status": "success",
                        "url": audio_url,
                        "local_path": local_path,
                        "duration_seconds": duration,
                        "error": None,
                    }

            return result

    except Exception as e:
        logger.error(f"Suno music generation failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "url": None,
            "local_path": None,
            "duration_seconds": None,
        }


async def _poll_suno_job(
    client: httpx.AsyncClient,
    headers: dict,
    job_id: str,
    max_attempts: int = 30,
    poll_interval: float = 2.0,
) -> dict:
    """
    Poll Suno job status until completion or failure.
    """
    for attempt in range(max_attempts):
        try:
            resp = await client.get(
                f"{SUNO_API_BASE}/job/{job_id}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status")
            if status == "complete":
                audio_url = data.get("audio_url")
                return {
                    "status": "success",
                    "audio_url": audio_url,
                    "error": None,
                }
            elif status == "failed":
                error_msg = data.get("error", "Suno job failed")
                return {
                    "status": "failed",
                    "error": error_msg,
                    "url": None,
                    "local_path": None,
                    "duration_seconds": None,
                }
            else:
                logger.info(f"Suno job {job_id} status: {status} (attempt {attempt + 1}/{max_attempts})")
                await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.warning(f"Polling Suno job {job_id} failed: {e}")
            await asyncio.sleep(poll_interval)

    return {
        "status": "failed",
        "error": f"Suno job timed out after {max_attempts} attempts",
        "url": None,
        "local_path": None,
        "duration_seconds": None,
    }


async def _download_audio(client: httpx.AsyncClient, url: str, local_path: str) -> None:
    """
    Download audio from URL to local path.
    """
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Downloaded audio to {local_path} ({len(resp.content)} bytes)")
    except Exception as e:
        logger.error(f"Failed to download audio from {url}: {e}")
        raise


async def _get_audio_duration(local_path: str) -> float:
    """
    Get audio duration using ffprobe.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            local_path,
        ]
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await result.communicate()
        if result.returncode == 0:
            return float(stdout.decode().strip())
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {e}")
    return 0.0


async def generate_bgm_track(
    title: str,
    description: str,
    genre: str = "ambient",
    duration: int = 30,
    instrumental: bool = True,
) -> dict:
    """
    Generate a BGM track with metadata using Suno.
    Returns dict with status, url, local_path, duration_seconds, and error.
    """
    prompt = f"{genre} {description}"
    return await generate_music(
        prompt=prompt,
        duration=duration,
        instrumental=instrumental,
    )