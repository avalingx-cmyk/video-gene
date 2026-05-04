import pytest
from unittest.mock import MagicMock, patch
from app.tasks.video_generation import (
    generate_video_task,
    RETRY_DELAYS,
    _get_jittered_delay,
)


class TestRetryDelays:
    def test_retry_delays_has_five_values(self):
        assert len(RETRY_DELAYS) == 5

    def test_retry_delays_are_increasing(self):
        assert RETRY_DELAYS == [1, 2, 5, 10, 30]


class TestGetJitteredDelay:
    def test_first_attempt_returns_around_1_second(self):
        delay = _get_jittered_delay(0)
        assert 0.5 <= delay <= 1.5

    def test_second_attempt_returns_around_2_seconds(self):
        delay = _get_jittered_delay(1)
        assert 1.0 <= delay <= 3.0

    def test_exhausted_delays_returns_final_value(self):
        delay = _get_jittered_delay(10)
        assert 15 <= delay <= 45


class TestGenerateVideoTask:
    def test_task_is_bound(self):
        assert hasattr(generate_video_task, 'bind')

    def test_task_max_retries_matches_retry_delays_length(self):
        assert generate_video_task.max_retries == len(RETRY_DELAYS)