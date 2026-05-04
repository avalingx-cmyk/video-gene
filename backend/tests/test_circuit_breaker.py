import pytest
import asyncio
from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ProviderHealthTracker,
    get_provider_health,
)


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_record_success_resets_failure_count(self):
        cb = CircuitBreaker()
        cb.failure_count = 2
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_record_failure_increments_count(self):
        cb = CircuitBreaker()
        cb.record_failure()
        assert cb.failure_count == 1

    def test_opens_after_failure_threshold(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_can_attempt_closed_state(self):
        cb = CircuitBreaker()
        assert cb.can_attempt() is True

    def test_can_attempt_open_state_before_recovery(self):
        cb = CircuitBreaker(state=CircuitState.OPEN, failure_count=3, last_failure_time=asyncio.get_event_loop().time())
        assert cb.can_attempt() is False

    def test_half_open_allows_one_attempt(self):
        cb = CircuitBreaker(state=CircuitState.HALF_OPEN, half_open_calls=1)
        assert cb.can_attempt() is True

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(state=CircuitState.HALF_OPEN, half_open_calls=1, config=CircuitBreakerConfig(failure_threshold=3))
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_trips_after_3_failures(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=300))
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_recovers_after_5_minutes(self):
        cb = CircuitBreaker(state=CircuitState.OPEN, failure_count=3, last_failure_time=0)
        cb.config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=300)
        import time
        cb.last_failure_time = time.time() - 301
        assert cb.can_attempt() is True
        assert cb.state == CircuitState.HALF_OPEN


class TestProviderHealthTracker:
    @pytest.fixture
    def tracker(self):
        return ProviderHealthTracker()

    def test_get_breaker_creates_new(self, tracker):
        breaker = tracker.get_breaker("test_provider")
        assert breaker is not None
        assert breaker.state == CircuitState.CLOSED

    def test_get_breaker_returns_same_instance(self, tracker):
        b1 = tracker.get_breaker("test_provider")
        b2 = tracker.get_breaker("test_provider")
        assert b1 is b2

    def test_record_success_clears_failures(self, tracker):
        breaker = tracker.get_breaker("test_provider", CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            breaker.record_failure()
        assert breaker.failure_count == 3
        asyncio.run(tracker.record_success("test_provider"))
        assert breaker.failure_count == 0

    def test_record_failure_updates_breaker(self, tracker):
        asyncio.run(tracker.record_failure("test_provider"))
        assert tracker.get_state("test_provider") == CircuitState.OPEN

    def test_can_attempt_unknown_provider_returns_true(self, tracker):
        result = asyncio.run(tracker.can_attempt("unknown_provider"))
        assert result is True

    def test_is_available_for_new_provider(self, tracker):
        assert tracker.is_available("new_provider") is True

    def test_is_available_open_provider(self, tracker):
        breaker = tracker.get_breaker("test_provider", CircuitBreakerConfig(failure_threshold=2))
        breaker.state = CircuitState.OPEN
        assert tracker.is_available("test_provider") is False


class TestGetProviderHealth:
    def test_singleton_returns_same_instance(self):
        h1 = get_provider_health()
        h2 = get_provider_health()
        assert h1 is h2