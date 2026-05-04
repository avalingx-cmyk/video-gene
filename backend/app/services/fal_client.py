import asyncio
import logging
import os
import uuid

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

HAPPY_HORSE_MODEL = "fal-ai/hunyuan-video"

SETTINGS = get_settings()


async def generate_video_segment(
    prompt: str,
    duration_seconds: float = 10.0,
    aspect_ratio: str = "9:16",
    output_dir: str | None = None,
) -> str:
    api_key = SETTINGS.fal_api_key
    if not api_key:
        raise RuntimeError("FAL_API_KEY not configured")

    resolution = _parse_aspect_ratio(aspect_ratio)

    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            "https://queue.fal.run/" + HAPPY_HORSE_MODEL,
            headers={
                "Authorization": f"Key {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "negative_prompt": "text, letters, words, watermark, subtitle, caption, blurry, low quality",
                "num_frames": _duration_to_frames(duration_seconds),
                "resolution": resolution,
                "enable_audio": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        request_id = data.get("request_id")
        if not request_id:
            raise RuntimeError(f"fal.ai: no request_id in response: {data}")

        logger.info(f"fal.ai: submitted request {request_id}, polling for completion")
        result = await _poll_fal(client, api_key, request_id)
        video_url = result.get("video", {}).get("url")
        if not video_url:
            raise RuntimeError(f"fal.ai: no video URL in result: {result}")

        local_path = await _download_video(client, video_url, output_dir)
        return local_path


async def _poll_fal(client: httpx.AsyncClient, api_key: str, request_id: str) -> dict:
    status_url = f"https://queue.fal.run/{HAPPY_HORSE_MODEL}/requests/{request_id}/status"
    result_url = f"https://queue.fal.run/{HAPPY_HORSE_MODEL}/requests/{request_id}"

    for _ in range(120):
        await asyncio.sleep(5)
        resp = await client.get(
            status_url,
            headers={"Authorization": f"Key {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")

        if status == "COMPLETED":
            resp2 = await client.get(
                result_url,
                headers={"Authorization": f"Key {api_key}"},
            )
            resp2.raise_for_status()
            return resp2.json()

        if status == "FAILED":
            raise RuntimeError(f"fal.ai generation failed: {data.get('error', 'unknown')}")

        logger.debug(f"fal.ai: request {request_id} status={status}")

    raise RuntimeError("fal.ai: polling timed out after 10 minutes")


async def _download_video(client: httpx.AsyncClient, url: str, output_dir: str | None) -> str:
    out_dir = output_dir or SETTINGS.output_dir
    os.makedirs(out_dir, exist_ok=True)
    local_path = os.path.join(out_dir, f"{uuid.uuid4()}.mp4")

    resp = await client.get(url, follow_redirects=True)
    resp.raise_for_status()

    with open(local_path, "wb") as f:
        f.write(resp.content)

    logger.info(f"Downloaded video to {local_path} ({len(resp.content)} bytes)")
    return local_path


def _duration_to_frames(duration_seconds: float) -> int:
    fps = 24
    min_frames = 25
    max_frames = 129
    frames = int(duration_seconds * fps)
    frames = max(min_frames, min(max_frames, frames))
    if frames % 2 != 0:
        frames += 1
    return frames


def _parse_aspect_ratio(ratio: str) -> str:
    mapping = {
        "9:16": "1080x1920",
        "16:9": "1920x1080",
        "1:1": "1080x1080",
    }
    return mapping.get(ratio, "1080x1920")