import asyncio
import logging
from typing import Optional

from .circuit_breaker import ProviderHealthTracker, get_provider_health, CircuitState

logger = logging.getLogger(__name__)

_HEALTH_CHECK_CONFIGS = {
    "zsky": {"timeout": 10.0, "endpoint": "https://api.zsky.ai/v1/health"},
    "happy_horse": {"timeout": 10.0, "endpoint": "https://api.happyhorse.ai/v1/health"},
    "free_ai": {"timeout": 10.0, "endpoint": "https://free.ai/api/v1/health"},
}


async def check_provider_health(provider: str) -> bool:
    import httpx

    config = _HEALTH_CHECK_CONFIGS.get(provider)
    if not config:
        return True

    try:
        async with httpx.AsyncClient(timeout=config["timeout"]) as client:
            resp = await client.get(config["endpoint"])
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Health check failed for {provider}: {e}")
        return False


async def refresh_provider_health() -> dict[str, bool]:
    health = get_provider_health()
    results = {}

    async def check_and_record(provider: str):
        ok = await check_provider_health(provider)
        if ok:
            await health.record_success(provider)
        else:
            await health.record_failure(provider)
        results[provider] = ok

    await asyncio.gather(*(check_and_record(p) for p in _HEALTH_CHECK_CONFIGS))
    return results


def get_health_summary() -> dict:
    health = get_provider_health()
    summary = {}
    for provider in _HEALTH_CHECK_CONFIGS:
        state = health.get_state(provider)
        summary[provider] = {
            "state": state.value,
            "available": health.is_available(provider),
        }
    return summary