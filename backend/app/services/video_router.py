from enum import Enum
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class Provider(Enum):
    ZSKY = "zsky"
    HAPPY_HORSE = "happy_horse"
    FREE_AI = "free_ai"
    VEO3 = "veo3"
    GENBO = "genbo"


PROVIDER_PRIORITY = [
    Provider.ZSKY,
    Provider.HAPPY_HORSE,
    Provider.FREE_AI,
]

PROVIDER_CAPABILITIES = {
    Provider.ZSKY: {
        "max_length_seconds": 10,
        "supports_portrait": True,
        "native_audio": True,
        "cost_tier": "free",
        "rate_limit": "10 req/min",
        "free_tier": "unlimited (ad-supported)",
    },
    Provider.HAPPY_HORSE: {
        "max_length_seconds": 30,
        "supports_portrait": True,
        "native_audio": True,
        "cost_tier": "free_trial",
        "rate_limit": "10 free credits",
        "free_tier": "10 free credits",
    },
    Provider.FREE_AI: {
        "max_length_seconds": 60,
        "supports_portrait": False,
        "native_audio": False,
        "cost_tier": "free",
        "rate_limit": "25-50 videos/day",
        "free_tier": "2.5K-5K tokens/day",
    },
    Provider.VEO3: {
        "max_length_seconds": 300,
        "supports_portrait": True,
        "native_audio": True,
        "cost_tier": "freemium",
        "rate_limit": "2 concurrent",
        "free_tier": "100 credits/month (~20 videos)",
    },
    Provider.GENBO: {
        "max_length_seconds": 120,
        "supports_portrait": False,
        "native_audio": False,
        "cost_tier": "paid",
        "rate_limit": "high",
        "free_tier": "none ($0.005-$0.012/video)",
    },
}


def select_provider(length_seconds: int, style: str) -> Optional[Provider]:
    for provider in PROVIDER_PRIORITY:
        caps = PROVIDER_CAPABILITIES[provider]
        if length_seconds <= caps["max_length_seconds"]:
            return provider
    return Provider.ZSKY


async def _call_zsky(prompt: str, length_seconds: int) -> str:
    """ZSky AI: truly free, no API key, 1080p+audio native, 10s max."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            "https://api.zsky.ai/v1/video/generate",
            json={
                "prompt": prompt,
                "duration": min(length_seconds, 10),
                "resolution": "1080x1920",
                "audio": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            raise RuntimeError(f"ZSky: no task_id in response: {data}")

        video_url = await _poll_zsky(client, task_id)
        return video_url


async def _poll_zsky(client: httpx.AsyncClient, task_id: str) -> str:
    import asyncio

    for _ in range(60):
        await asyncio.sleep(5)
        resp = await client.get(f"https://api.zsky.ai/v1/video/status/{task_id}")
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")
        if status == "completed":
            return data["video_url"]
        if status == "failed":
            raise RuntimeError(f"ZSky generation failed: {data.get('error', 'unknown')}")
    raise RuntimeError("ZSky: polling timed out after 5 minutes")


async def _call_happy_horse(prompt: str, length_seconds: int) -> str:
    """Happy Horse AI: #1 ranked, 1080p+audio, 10 free credits."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            "https://api.happyhorse.ai/v1/generate",
            json={
                "prompt": prompt,
                "duration": min(length_seconds, 30),
                "resolution": "1080x1920",
                "audio": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            raise RuntimeError(f"Happy Horse: no task_id in response: {data}")

        video_url = await _poll_happy_horse(client, task_id)
        return video_url


async def _poll_happy_horse(client: httpx.AsyncClient, task_id: str) -> str:
    import asyncio

    for _ in range(60):
        await asyncio.sleep(5)
        resp = await client.get(f"https://api.happyhorse.ai/v1/status/{task_id}")
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")
        if status == "completed":
            return data["video_url"]
        if status == "failed":
            raise RuntimeError(f"Happy Horse generation failed: {data.get('error', 'unknown')}")
    raise RuntimeError("Happy Horse: polling timed out after 5 minutes")


async def _call_free_ai(prompt: str, length_seconds: int) -> str:
    """Free.ai CogVideoX: ~25-50 free videos/day, no audio, variable resolution."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            "https://free.ai/api/v1/cogvideox/generate",
            json={
                "prompt": prompt,
                "duration": min(length_seconds, 60),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            raise RuntimeError(f"Free.ai: no task_id in response: {data}")

        video_url = await _poll_free_ai(client, task_id)
        return video_url


async def _poll_free_ai(client: httpx.AsyncClient, task_id: str) -> str:
    import asyncio

    for _ in range(60):
        await asyncio.sleep(5)
        resp = await client.get(f"https://free.ai/api/v1/status/{task_id}")
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")
        if status == "completed":
            return data["video_url"]
        if status == "failed":
            raise RuntimeError(f"Free.ai generation failed: {data.get('error', 'unknown')}")
    raise RuntimeError("Free.ai: polling timed out after 5 minutes")


PROVIDER_CALLS = {
    Provider.ZSKY: _call_zsky,
    Provider.HAPPY_HORSE: _call_happy_horse,
    Provider.FREE_AI: _call_free_ai,
}


async def generate_with_provider(provider: Provider, prompt: str, length_seconds: int) -> str:
    """Submit generation request to a specific provider. Returns video URL."""
    if provider not in PROVIDER_CALLS:
        raise NotImplementedError(f"Provider {provider.value} not yet implemented")
    return await PROVIDER_CALLS[provider](prompt, length_seconds)


async def generate_with_router(prompt: str, style: str, length_seconds: int) -> str:
    """Route generation request through provider selection with fallback chain."""
    primary = select_provider(length_seconds, style)
    last_error = None

    for provider in PROVIDER_PRIORITY:
        if PROVIDER_CAPABILITIES[provider]["max_length_seconds"] < length_seconds:
            continue
        try:
            logger.info(f"Attempting generation with provider: {provider.value}")
            return await generate_with_provider(provider, prompt, length_seconds)
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Provider {provider.value} failed: {last_error}")
            continue

    raise RuntimeError(f"All providers failed. Last error: {last_error}")
