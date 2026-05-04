import asyncio
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.core.config import get_settings
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.video import User
from app.services.ffmpeg_service import combine_audio_streams

logger = logging.getLogger(__name__)
SETTINGS = get_settings()

router = APIRouter()


class MixRequest(BaseModel):
    tts_audio_path: str
    bgm_audio_path: str
    tts_volume: float = 1.0
    bgm_volume: float = 0.5
    fade_out_seconds: float = 2.0
    output_filename: Optional[str] = None


class MixResponse(BaseModel):
    status: str
    output_path: str
    duration_seconds: float
    error: Optional[str] = None


async def _get_audio_duration(local_path: str) -> float:
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


@router.post("/mix", response_model=MixResponse)
async def mix_audio(
    request: MixRequest,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """
    Mix TTS audio with BGM music.
    Applies volume levels, optional fade out, and outputs combined audio.
    """
    out_dir = SETTINGS.output_dir
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(request.tts_audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TTS audio not found: {request.tts_audio_path}",
        )

    if not os.path.exists(request.bgm_audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BGM audio not found: {request.bgm_audio_path}",
        )

    output_filename = request.output_filename or f"{uuid.uuid4()}.mp3"
    output_path = os.path.join(out_dir, output_filename)

    try:
        await combine_audio_streams(
            tts_path=request.tts_audio_path,
            bgm_path=request.bgm_audio_path,
            output_path=output_path,
            tts_volume=request.tts_volume,
            bgm_volume=request.bgm_volume,
            fade_out_seconds=request.fade_out_seconds,
        )

        duration = await _get_audio_duration(output_path)

        return MixResponse(
            status="success",
            output_path=output_path,
            duration_seconds=duration,
            error=None,
        )

    except Exception as e:
        logger.error(f"Audio mixing failed: {e}")
        return MixResponse(
            status="failed",
            output_path=output_path,
            duration_seconds=0.0,
            error=str(e),
        )


@router.post("/generate-mix")
async def generate_mix(
    text: str,
    prompt: str,
    voice: str = "af_heart",
    genre: str = "ambient",
    tts_volume: float = 1.0,
    bgm_volume: float = 0.5,
    fade_out_seconds: float = 2.0,
    db=None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate TTS and BGM, then mix them together.
    Returns the final mixed audio path.
    """
    from app.services.tts_pipeline import generate_tts_for_segment
    from app.services.suno_service import generate_music

    tts_result = await generate_tts_for_segment(
        text=text,
        voice=voice,
    )

    if tts_result["status"] != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {tts_result.get('error')}",
        )

    bgm_result = await generate_music(
        prompt=f"{genre} {prompt}",
        duration=int(tts_result["duration_seconds"]) + 5,
        instrumental=True,
    )

    if bgm_result["status"] != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BGM generation failed: {bgm_result.get('error')}",
        )

    out_dir = SETTINGS.output_dir
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, f"{uuid.uuid4()}.mp3")

    try:
        await combine_audio_streams(
            tts_path=tts_result["local_path"],
            bgm_path=bgm_result["local_path"],
            output_path=output_path,
            tts_volume=tts_volume,
            bgm_volume=bgm_volume,
            fade_out_seconds=fade_out_seconds,
        )

        duration = await _get_audio_duration(output_path)

        return {
            "status": "success",
            "tts_path": tts_result["local_path"],
            "bgm_path": bgm_result["local_path"],
            "output_path": output_path,
            "duration_seconds": duration,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Mixed audio generation failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
        }