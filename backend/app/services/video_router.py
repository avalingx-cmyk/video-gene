from enum import Enum


class Provider(Enum):
    REPLICATE = "replicate"
    RUNWAY = "runway"
    PIKA = "pika"
    LUMA = "luma"


PROVIDER_PRIORITY = [Provider.REPLICATE, Provider.RUNWAY, Provider.PIKA, Provider.LUMA]

PROVIDER_CAPABILITIES = {
    Provider.REPLICATE: {
        "max_length_seconds": 120,
        "supports_portrait": True,
        "cost_tier": "low",
    },
    Provider.RUNWAY: {
        "max_length_seconds": 60,
        "supports_portrait": True,
        "cost_tier": "medium",
    },
    Provider.PIKA: {
        "max_length_seconds": 30,
        "supports_portrait": True,
        "cost_tier": "low",
    },
    Provider.LUMA: {
        "max_length_seconds": 300,
        "supports_portrait": True,
        "cost_tier": "medium",
    },
}


def select_provider(length_seconds: int, style: str) -> Provider:
    """Select the best provider based on video length, style, and cost optimization."""
    for provider in PROVIDER_PRIORITY:
        caps = PROVIDER_CAPABILITIES[provider]
        if length_seconds <= caps["max_length_seconds"]:
            return provider

    # Default to longest-capability provider
    return Provider.LUMA


async def generate_with_provider(provider: Provider, prompt: str, length_seconds: int) -> str:
    """Submit generation request to a specific provider. Returns video URL."""
    # TODO: Implement actual API calls for each provider
    raise NotImplementedError(f"Provider {provider.value} not yet implemented")


async def generate_with_router(prompt: str, style: str, length_seconds: int) -> str:
    """Route generation request through provider selection with fallback chain."""
    provider = select_provider(length_seconds, style)
    last_error = None

    for p in PROVIDER_PRIORITY:
        if PROVIDER_CAPABILITIES[p]["max_length_seconds"] < length_seconds:
            continue
        try:
            return await generate_with_provider(p, prompt, length_seconds)
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"All providers failed. Last error: {last_error}")
