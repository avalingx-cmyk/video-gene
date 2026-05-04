import asyncio
import os
import tempfile

import pytest
import ffmpeg


pytestmark = pytest.mark.e2e


class TestAVSync:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_video(self, temp_dir):
        path = os.path.join(temp_dir, "sample.mp4")
        probe = ffmpeg.input("testsrc=duration=5:size=320x240:rate=30").output(
            path,
            vcodec="libx264",
            t=5,
            pix_fmt="yuv420p",
        )
        ffmpeg.run(probe, overwrite_output=True, quiet=True)
        return path

    @pytest.fixture
    def sample_audio(self, temp_dir):
        path = os.path.join(temp_dir, "sample.mp3")
        probe = ffmpeg.input("sine=frequency=440:duration=3").output(
            path,
            acodec="libmp3lame",
            t=3,
        )
        ffmpeg.run(probe, overwrite_output=True, quiet=True)
        return path

    def test_probe_duration_accuracy(self, sample_video):
        from app.services.audio_sync import probe_duration

        loop = asyncio.new_event_loop()
        duration = loop.run_until_complete(probe_duration(sample_video))
        loop.close()
        assert 4.5 <= duration <= 5.5

    def test_sync_validation_result_fields(self):
        from app.services.audio_sync import SyncValidationResult

        result = SyncValidationResult(
            segment_id="test-seg-1",
            video_actual_duration=10.0,
            tts_actual_duration=10.2,
            drift_seconds=0.2,
            offset_ms=200.0,
            status="ok",
            within_contract=True,
        )
        assert result.segment_id == "test-seg-1"
        assert result.within_contract is True
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_duration_lock_truncation(self):
        from app.services.audio_sync import enforce_duration_lock

        long_text = "This is a very long narration text that needs to be truncated to fit within the target duration lock period of approximately ten seconds for proper AV sync during video generation."
        target_dur = 10.0
        result = await enforce_duration_lock(long_text, target_dur, voice_id="af_heart")
        assert len(result) <= len(long_text)
        assert len(result) > 0

    def test_duration_drift_calculation(self):
        from app.services.audio_sync import calculate_duration_drift

        drift, drift_pct = calculate_duration_drift(expected=10.0, actual=10.5)
        assert abs(drift - 0.5) < 0.01
        assert abs(drift_pct - 5.0) < 0.1

    @pytest.mark.asyncio
    async def test_ffmpeg_integration_healthy(self):
        from app.services.audio_sync import validate_ffmpeg_integration

        result = await validate_ffmpeg_integration()
        assert result is True