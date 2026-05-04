import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid


class TestSunoService:

    @pytest.mark.asyncio
    async def test_generate_music_missing_api_key(self):
        with patch("app.services.suno_service.SETTINGS") as mock_settings:
            mock_settings.suno_api_key = ""
            mock_settings.output_dir = "/tmp/test_output"

            from app.services.suno_service import generate_music

            result = await generate_music(prompt="ambient chill")

            assert result["status"] == "failed"
            assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_bgm_track_missing_api_key(self):
        with patch("app.services.suno_service.SETTINGS") as mock_settings:
            mock_settings.suno_api_key = ""
            mock_settings.output_dir = "/tmp/test_output"

            from app.services.suno_service import generate_bgm_track

            result = await generate_bgm_track(
                title="Test Track",
                description="calm ambient music",
                genre="ambient",
            )

            assert result["status"] == "failed"
            assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_get_audio_duration_success(self):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = AsyncMock(
                returncode=0,
                communicate=AsyncMock(return_value=(b"123.456", b"")),
            )

            from app.services.suno_service import _get_audio_duration

            duration = await _get_audio_duration("/tmp/test.mp3")

            assert duration == 123.456

    @pytest.mark.asyncio
    async def test_get_audio_duration_failure(self):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = AsyncMock(
                returncode=1,
                communicate=AsyncMock(return_value=(b"", b"error")),
            )

            from app.services.suno_service import _get_audio_duration

            duration = await _get_audio_duration("/tmp/nonexistent.mp3")

            assert duration == 0.0

    @pytest.mark.asyncio
    async def test_download_audio_success(self):
        mock_response = MagicMock()
        mock_response.content = b"fake audio data"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        from app.services.suno_service import _download_audio

        with patch("app.services.suno_service.os.makedirs"):
            await _download_audio(mock_client, "https://example.com/audio.mp3", "/tmp/test.mp3")

        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_suno_job_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "complete",
            "audio_url": "https://example.com/audio.mp3",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        from app.services.suno_service import _poll_suno_job

        result = await _poll_suno_job(mock_client, {}, "job-123", max_attempts=1)

        assert result["status"] == "success"
        assert result["audio_url"] == "https://example.com/audio.mp3"

    @pytest.mark.asyncio
    async def test_poll_suno_job_failed(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "failed", "error": "Generation failed"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        from app.services.suno_service import _poll_suno_job

        result = await _poll_suno_job(mock_client, {}, "job-123", max_attempts=1)

        assert result["status"] == "failed"
        assert "failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_poll_suno_job_timeout(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "processing"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        from app.services.suno_service import _poll_suno_job

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await _poll_suno_job(mock_client, {}, "job-123", max_attempts=2, poll_interval=0.01)

        assert result["status"] == "failed"
        assert "timed out" in result["error"].lower()