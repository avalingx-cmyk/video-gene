import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.segment_pipeline import (
    validate_tts_video_sync,
    compute_tts_padding_needed,
    DURATION_TOLERANCE_SECONDS,
    TTS_DURATION_TOLERANCE_SECONDS,
    MAX_TTS_RESYNC_ATTEMPTS,
)
from app.services.ffmpeg_service import (
    measure_audio_sync_drift,
    extend_audio_to_duration,
)
from app.models.segment import SegmentStatus, AudioSyncStatus


class TestValidateTtsVideoSync:
    def test_synced_within_tolerance(self):
        is_synced, drift, msg = validate_tts_video_sync(
            tts_actual_duration=10.1,
            video_actual_duration=10.0,
            target_duration=10.0,
        )
        assert is_synced is True
        assert abs(drift) <= TTS_DURATION_TOLERANCE_SECONDS

    def test_tts_too_long(self):
        is_synced, drift, msg = validate_tts_video_sync(
            tts_actual_duration=12.0,
            video_actual_duration=10.0,
            target_duration=10.0,
        )
        assert is_synced is False
        assert drift == 2.0

    def test_tts_too_short(self):
        is_synced, drift, msg = validate_tts_video_sync(
            tts_actual_duration=8.0,
            video_actual_duration=10.0,
            target_duration=10.0,
        )
        assert is_synced is False
        assert drift == -2.0

    def test_video_out_of_tolerance_but_tts_ok(self):
        is_synced, drift, msg = validate_tts_video_sync(
            tts_actual_duration=10.0,
            video_actual_duration=10.6,
            target_duration=10.0,
        )
        assert is_synced is False

    def test_both_within_tolerance(self):
        is_synced, drift, msg = validate_tts_video_sync(
            tts_actual_duration=10.1,
            video_actual_duration=10.2,
            target_duration=10.0,
        )
        assert is_synced is True


class TestComputeTtsPaddingNeeded:
    def test_no_padding_needed(self):
        padding = compute_tts_padding_needed(10.0, 10.0)
        assert padding == 0.0

    def test_padding_needed(self):
        padding = compute_tts_padding_needed(8.0, 10.0)
        assert padding == 2.0

    def test_tts_longer_than_target(self):
        padding = compute_tts_padding_needed(12.0, 10.0)
        assert padding == 0.0


class TestMeasureAudioSyncDrift:
    @pytest.mark.asyncio
    async def test_measure_drift(self):
        with patch("app.services.ffmpeg_service.probe_duration") as mock_probe:
            mock_probe.side_effect = [10.0, 10.3]
            drift, offset_ms = await measure_audio_sync_drift("/fake/video.mp4", "/fake/tts.mp3")
            assert abs(offset_ms - 300) < 1

    @pytest.mark.asyncio
    async def test_negative_drift(self):
        with patch("app.services.ffmpeg_service.probe_duration") as mock_probe:
            mock_probe.side_effect = [10.0, 9.5]
            drift, offset_ms = await measure_audio_sync_drift("/fake/video.mp4", "/fake/tts.mp3")
            assert drift == -0.5
            assert offset_ms == 500


class TestExtendAudioToDuration:
    @pytest.mark.asyncio
    async def test_audio_already_long_enough(self):
        with patch("app.services.ffmpeg_service.probe_duration") as mock_probe, \
             patch("app.services.ffmpeg_service._copy_file") as mock_copy:
            mock_probe.return_value = 12.0
            result = await extend_audio_to_duration("/fake/tts.mp3", 10.0)
            mock_copy.assert_called_once()
            assert result.endswith("_padded.mp3")

    @pytest.mark.asyncio
    async def test_audio_padded_with_apad(self):
        with patch("app.services.ffmpeg_service.probe_duration") as mock_probe, \
             patch("app.services.ffmpeg_service._run") as mock_run, \
             patch("app.services.ffmpeg_service._copy_file") as mock_copy:
            mock_probe.return_value = 8.0
            mock_run.side_effect = Exception("apad failed")
            mock_copy.return_value = "/fake/tts_padded.mp3"
            result = await extend_audio_to_duration("/fake/tts.mp3", 10.0, "/fake/padded.mp3")
            assert result == "/fake/padded.mp3"


class TestSegmentStatusTransitions:
    def test_tts_resync_needed_status_exists(self):
        assert SegmentStatus.tts_resync_needed == "tts_resync_needed"

    def test_all_statuses_are_strings(self):
        for status in SegmentStatus:
            assert isinstance(status.value, str)


class TestAudioSyncConstants:
    def test_tolerance_values(self):
        assert DURATION_TOLERANCE_SECONDS == 0.5
        assert TTS_DURATION_TOLERANCE_SECONDS == 0.5
        assert MAX_TTS_RESYNC_ATTEMPTS == 2

    def test_max_tts_resync_within_expected_range(self):
        assert MAX_TTS_RESYNC_ATTEMPTS <= 3
