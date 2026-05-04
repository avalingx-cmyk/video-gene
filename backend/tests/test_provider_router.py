import pytest
from app.services.video_router import (
    Provider,
    PROVIDER_PRIORITY,
    PROVIDER_CAPABILITIES,
    select_provider,
    get_provider_status,
)


class TestProviderEnum:
    def test_all_expected_providers_exist(self):
        expected = {Provider.ZSKY, Provider.HAPPY_HORSE, Provider.FREE_AI}
        assert set(PROVIDER_PRIORITY).issuperset(expected)

    def test_provider_capabilities_complete(self):
        for provider in PROVIDER_PRIORITY:
            caps = PROVIDER_CAPABILITIES[provider]
            assert "max_length_seconds" in caps
            assert "supports_portrait" in caps
            assert "cost_tier" in caps


class TestSelectProvider:
    def test_zsky_for_short_videos(self):
        p = select_provider(5, "anime")
        assert p == Provider.ZSKY

    def test_zsky_for_10s(self):
        p = select_provider(10, "anime")
        assert p == Provider.ZSKY

    def test_happy_horse_for_15s(self):
        p = select_provider(15, "anime")
        assert p == Provider.HAPPY_HORSE

    def test_happy_horse_for_30s(self):
        p = select_provider(30, "anime")
        assert p == Provider.HAPPY_HORSE

    def test_free_ai_for_45s(self):
        p = select_provider(45, "anime")
        assert p == Provider.FREE_AI

    def test_falls_back_to_free_ai_for_long(self):
        p = select_provider(60, "anime")
        assert p == Provider.FREE_AI


class TestGetProviderStatus:
    def test_returns_all_providers(self):
        status = get_provider_status()
        for provider in PROVIDER_PRIORITY:
            assert provider.value in status

    def test_status_includes_state_and_available(self):
        status = get_provider_status()
        for provider_key, info in status.items():
            assert "state" in info
            assert "available" in info
            assert isinstance(info["available"], bool)