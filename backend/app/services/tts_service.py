import asyncio
import logging
import os
import uuid

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
SETTINGS = get_settings()

ORPHEUS_MODEL = "ORYX/oryx-higher"


async def generate_tts_segment(
    text: str,
    voice: str = "af_heart",
) -> dict:
    out_dir = SETTINGS.output_dir
    os.makedirs(out_dir, exist_ok=True)
    local_path = os.path.join(out_dir, f"{uuid.uuid4()}.mp3")

    api_key = SETTINGS.groq_api_key
    if not api_key:
        return {"status": "failed", "error": "GROQ_API_KEY not configured", "url": None, "local_path": None, "duration_seconds": None}

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": ORPHEUS_MODEL,
                        "input": text,
                        "voice": voice,
                        "response_format": "mp3",
                    },
                )
                resp.raise_for_status()

                with open(local_path, "wb") as f:
                    f.write(resp.content)

                duration = await _get_audio_duration(local_path)
                return {
                    "status": "success",
                    "url": None,
                    "local_path": local_path,
                    "duration_seconds": duration,
                    "error": None,
                }
        except Exception as e:
            logger.warning(f"TTS attempt {attempt + 1} failed: {e}")
            continue

    return {"status": "failed", "error": f"TTS failed after 3 retries", "url": None, "local_path": None, "duration_seconds": None}


async def _get_audio_duration(local_path: str) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            local_path
        ]
        result = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await result.communicate()
        if result.returncode == 0:
            return float(stdout.decode().strip())
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {e}")
    return 0.0