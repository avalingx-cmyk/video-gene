import asyncio
import time
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout: int = 60
    half_open_max_calls: int = 1


@dataclass
class CircuitBreaker:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = field(default=None, repr=False)
    half_open_calls: int = 0
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls -= 1
            if self.half_open_calls <= 0:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful recovery")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened after failure in half-open state")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None:
                return True
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = self.config.half_open_max_calls
                logger.info("Circuit breaker entering half-open state")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls > 0

        return False

    def get_state(self) -> CircuitState:
        return self.state


class ProviderHealthTracker:
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get_breaker(self, provider: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        if provider not in self._breakers:
            self._breakers[provider] = CircuitBreaker(config=config or CircuitBreakerConfig())
        return self._breakers[provider]

    async def record_success(self, provider: str) -> None:
        async with self._lock:
            if provider in self._breakers:
                self._breakers[provider].record_success()

    async def record_failure(self, provider: str) -> None:
        async with self._lock:
            breaker = self.get_breaker(provider)
            breaker.record_failure()

    async def can_attempt(self, provider: str) -> bool:
        if provider not in self._breakers:
            return True
        return self._breakers[provider].can_attempt()

    def get_state(self, provider: str) -> CircuitState:
        return self._breakers.get(provider, CircuitBreaker()).get_state()

    def is_available(self, provider: str) -> bool:
        state = self.get_state(provider)
        return state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)


_provider_health = ProviderHealthTracker()


def get_provider_health() -> ProviderHealthTracker:
    return _provider_health