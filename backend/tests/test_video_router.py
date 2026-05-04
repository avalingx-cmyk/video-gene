import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.video_router import (
    Provider,
    PROVIDER_PRIORITY,
    PROVIDER_CAPABILITIES,
    CircuitBreakerConfig,
    generate_with_provider,
    generate_with_router,
    select_provider,
    get_provider_status,
    PROVIDER_CIRCUIT_BREAKER_CONFIGS,
)


class TestSelectProvider:
    def test_selects_zsky_for_short_video(self):
        result = select_provider(5, "realistic")
        assert result == Provider.ZSKY

    def test_selects_happy_horse_for_medium_video(self):
        result = select_provider(15, "anime")
        assert result == Provider.HAPPY_HORSE

    def test_selects_free_ai_for_long_video(self):
        result = select_provider(45, "abstract")
        assert result == Provider.FREE_AI


class TestGenerateWithProvider:
    @pytest.mark.asyncio
    async def test_records_success_on_successful_call(self):
        mock_result = "https://example.com/video.mp4"
        with patch("app.services.video_router.PROVIDER_CALLS", {
            Provider.ZSKY: AsyncMock(return_value=mock_result)
        }):
            with patch("app.services.video_router.get_provider_health") as mock_health:
                mock_tracker = MagicMock()
                mock_tracker.record_success = AsyncMock()
                mock_health.return_value = mock_tracker

                result = await generate_with_provider(Provider.ZSKY, "test prompt", 5)
                assert result == mock_result
                mock_tracker.record_success.assert_called_once_with(Provider.ZSKY.value)

    @pytest.mark.asyncio
    async def test_records_failure_on_exception(self):
        with patch("app.services.video_router.PROVIDER_CALLS", {
            Provider.ZSKY: AsyncMock(side_effect=Exception("Provider error"))
        }):
            with patch("app.services.video_router.get_provider_health") as mock_health:
                mock_tracker = MagicMock()
                mock_tracker.record_failure = AsyncMock()
                mock_health.return_value = mock_tracker

                with pytest.raises(Exception, match="Provider error"):
                    await generate_with_provider(Provider.ZSKY, "test prompt", 5)
                mock_tracker.record_failure.assert_called_once_with(Provider.ZSKY.value)


class TestGenerateWithRouter:
    @pytest.mark.asyncio
    async def test_skips_provider_with_open_circuit(self):
        with patch("app.services.video_router.PROVIDER_CALLS", {
            Provider.ZSKY: AsyncMock(side_effect=Exception("fail")),
            Provider.HAPPY_HORSE: AsyncMock(return_value="https://example.com/video.mp4"),
        }):
            with patch("app.services.video_router.get_provider_health") as mock_health:
                mock_tracker = MagicMock()
                mock_tracker.can_attempt = AsyncMock(side_effect=lambda p: p != Provider.ZSKY.value)
                mock_tracker.record_failure = AsyncMock()
                mock_tracker.record_success = AsyncMock()
                mock_health.return_value = mock_tracker

                result = await generate_with_router("test prompt", "realistic", 5)
                assert result == "https://example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_falls_back_to_second_provider_when_first_fails(self):
        with patch("app.services.video_router.PROVIDER_CALLS", {
            Provider.ZSKY: AsyncMock(side_effect=Exception("ZSky down")),
            Provider.HAPPY_HORSE: AsyncMock(return_value="https://happyhorse.ai/video.mp4"),
        }):
            with patch("app.services.video_router.get_provider_health") as mock_health:
                mock_tracker = MagicMock()
                mock_tracker.can_attempt = AsyncMock(return_value=True)
                mock_tracker.record_failure = AsyncMock()
                mock_tracker.record_success = AsyncMock()
                mock_health.return_value = mock_tracker

                result = await generate_with_router("test prompt", "realistic", 5)
                assert result == "https://happyhorse.ai/video.mp4"

    @pytest.mark.asyncio
    async def test_fallback_happens_quickly_with_5xx_error(self):
        import time
        start = time.time()
        with patch("app.services.video_router.PROVIDER_CALLS", {
            Provider.ZSKY: AsyncMock(side_effect=Exception("500 Server Error")),
            Provider.HAPPY_HORSE: AsyncMock(return_value="https://happyhorse.ai/video.mp4"),
        }):
            with patch("app.services.video_router.get_provider_health") as mock_health:
                mock_tracker = MagicMock()
                mock_tracker.can_attempt = AsyncMock(return_value=True)
                mock_tracker.record_failure = AsyncMock()
                mock_tracker.record_success = AsyncMock()
                mock_health.return_value = mock_tracker

                result = await generate_with_router("test prompt", "realistic", 5)
                elapsed = time.time() - start
                assert result == "https://happyhorse.ai/video.mp4"
                assert elapsed < 2.0


class TestGetProviderStatus:
    def test_returns_status_for_all_providers(self):
        status = get_provider_status()
        for provider in PROVIDER_PRIORITY:
            assert provider.value in status
            assert "state" in status[provider.value]
            assert "available" in status[provider.value]


class TestProviderCircuitBreakerConfigs:
    def test_configs_defined_for_all_priority_providers(self):
        for provider in PROVIDER_PRIORITY:
            assert provider in PROVIDER_CIRCUIT_BREAKER_CONFIGS
            config = PROVIDER_CIRCUIT_BREAKER_CONFIGS[provider]
            assert isinstance(config, CircuitBreakerConfig)
            assert config.failure_threshold > 0
            assert config.recovery_timeout > 0