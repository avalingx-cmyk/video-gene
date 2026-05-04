import pytest
from app.services.health import (
    _HEALTH_CHECK_CONFIGS,
    get_health_summary,
)


class TestHealthCheckConfigs:
    def test_all_required_providers_configured(self):
        expected = {"zsky", "happy_horse", "free_ai"}
        assert set(_HEALTH_CHECK_CONFIGS.keys()) == expected

    def test_each_config_has_timeout_and_endpoint(self):
        for provider, config in _HEALTH_CHECK_CONFIGS.items():
            assert "timeout" in config
            assert "endpoint" in config
            assert isinstance(config["timeout"], float)


class TestGetHealthSummary:
    def test_returns_all_configured_providers(self):
        summary = get_health_summary()
        for provider in _HEALTH_CHECK_CONFIGS:
            assert provider in summary

    def test_summary_includes_state_and_available(self):
        summary = get_health_summary()
        for provider, info in summary.items():
            assert "state" in info
            assert "available" in info
            assert isinstance(info["available"], bool)

    def test_state_values_are_valid_circuit_states(self):
        valid_states = {"closed", "open", "half_open"}
        summary = get_health_summary()
        for provider, info in summary.items():
            assert info["state"] in valid_states