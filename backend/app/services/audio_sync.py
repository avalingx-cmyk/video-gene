import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.services.ffmpeg_service import probe_duration

logger = logging.getLogger(__name__)


@dataclass
class DurationContract:
    segment_id: str
    expected_video_duration: float
    expected_tts_duration: float
    max_drift_seconds: float = 0.5


@dataclass
class SyncValidationResult:
    segment_id: str
    video_actual_duration: float | None
    tts_actual_duration: float | None
    drift_seconds: float
    offset_ms: float
    status: Literal["ok", "drift_detected", "untested"]
    within_contract: bool


async def validate_segment_sync(
    segment_id: str,
    video_path: str | None,
    tts_path: str | None,
    expected_duration: float,
    max_drift: float = 0.5,
) -> SyncValidationResult:
    if video_path is None or tts_path is None:
        return SyncValidationResult(
            segment_id=segment_id,
            video_actual_duration=None,
            tts_actual_duration=None,
            drift_seconds=0.0,
            offset_ms=0.0,
            status="untested",
            within_contract=False,
        )

    video_dur = await probe_duration(video_path)
    tts_dur = await probe_duration(tts_path)

    drift = tts_dur - video_dur
    offset_ms = abs(drift) * 1000

    status: Literal["ok", "drift_detected"] = (
        "ok" if abs(drift) <= max_drift else "drift_detected"
    )
    within_contract = abs(drift) <= max_drift

    return SyncValidationResult(
        segment_id=segment_id,
        video_actual_duration=video_dur,
        tts_actual_duration=tts_dur,
        drift_seconds=drift,
        offset_ms=offset_ms,
        status=status,
        within_contract=within_contract,
    )


async def measure_tts_duration_dry_run(
    text: str,
    voice_id: str = "af_heart",
) -> float:
    chars_per_second = 15.0
    char_count = len(text.strip())
    estimated_duration = char_count / chars_per_second
    return max(estimated_duration, 0.5)


def estimate_tts_char_rate(voice_id: str) -> float:
    rates = {
        "af_heart": 15.0,
        "af_nicole": 14.0,
        "af_sarah": 16.0,
        "am_michael": 14.5,
        "am_onyx": 13.0,
    }
    return rates.get(voice_id, 15.0)


async def enforce_duration_lock(
    tts_text: str,
    target_duration: float,
    voice_id: str = "af_heart",
) -> str:
    char_rate = estimate_tts_char_rate(voice_id)
    max_chars = int(target_duration * char_rate * 0.95)
    truncated = tts_text[:max_chars]
    return truncated


def calculate_duration_drift(
    expected: float,
    actual: float,
) -> tuple[float, float]:
    drift = actual - expected
    drift_percent = (drift / expected * 100) if expected > 0 else 0.0
    return drift, drift_percent


async def validate_ffmpeg_integration() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode == 0 and b"ffmpeg" in stdout
    except Exception as e:
        logger.error(f"FFmpeg validation failed: {e}")
        return False