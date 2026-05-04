import pytest
import uuid
import os
from unittest.mock import AsyncMock, patch, MagicMock


class TestMusicMixer:

    @pytest.mark.asyncio
    async def test_mix_audio_missing_tts_file(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.music_mixer import mix_audio, MixRequest

        with patch("app.api.v1.endpoints.music_mixer.SETTINGS") as mock_settings:
            mock_settings.output_dir = "/tmp/test_output"

            request = MixRequest(
                tts_audio_path="/nonexistent/tts.mp3",
                bgm_audio_path="/tmp/bgm.mp3",
                tts_volume=1.0,
                bgm_volume=0.5,
            )

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await mix_audio(request, db=mock_db, current_user=mock_current_user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_mix_audio_missing_bgm_file(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.music_mixer import mix_audio, MixRequest

        with patch("app.api.v1.endpoints.music_mixer.os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda path: path == "/tmp/tts.mp3"

            with patch("app.api.v1.endpoints.music_mixer.SETTINGS") as mock_settings:
                mock_settings.output_dir = "/tmp/test_output"

                request = MixRequest(
                    tts_audio_path="/tmp/tts.mp3",
                    bgm_audio_path="/nonexistent/bgm.mp3",
                    tts_volume=1.0,
                    bgm_volume=0.5,
                )

                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await mix_audio(request, db=mock_db, current_user=mock_current_user)
                assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_mix_audio_combines_successfully(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.music_mixer import mix_audio, MixRequest

        with patch("os.path.exists", return_value=True):
            with patch("app.api.v1.endpoints.music_mixer.SETTINGS") as mock_settings:
                mock_settings.output_dir = "/tmp/test_output"

                with patch("app.services.ffmpeg_service.combine_audio_streams", new_callable=AsyncMock) as mock_combine:
                    mock_combine.return_value = "/tmp/test_output/mixed.mp3"

                    with patch("asyncio.create_subprocess_exec") as mock_exec:
                        mock_exec.return_value = AsyncMock(
                            returncode=0,
                            communicate=AsyncMock(return_value=(b"10.5", b"")),
                        )

                        request = MixRequest(
                            tts_audio_path="/tmp/tts.mp3",
                            bgm_audio_path="/tmp/bgm.mp3",
                            tts_volume=1.0,
                            bgm_volume=0.5,
                        )

                        result = await mix_audio(request, db=mock_db, current_user=mock_current_user)

                        assert result.status == "success"
                        assert "mixed.mp3" in result.output_path

    @pytest.mark.asyncio
    async def test_generate_mix_tts_failure(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.music_mixer import generate_mix

        with patch("app.services.tts_pipeline.generate_tts_for_segment", new_callable=AsyncMock) as mock_tts:
            mock_tts.return_value = {"status": "failed", "error": "TTS error"}

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await generate_mix(
                    text="Hello world",
                    prompt="calm ambient",
                    db=mock_db,
                    current_user=mock_current_user,
                )
            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_generate_mix_bgm_failure(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.music_mixer import generate_mix

        with patch("app.services.tts_pipeline.generate_tts_for_segment", new_callable=AsyncMock) as mock_tts:
            mock_tts.return_value = {
                "status": "success",
                "local_path": "/tmp/tts.mp3",
                "duration_seconds": 10.0,
            }

            with patch("app.services.suno_service.generate_music", new_callable=AsyncMock) as mock_bgm:
                mock_bgm.return_value = {"status": "failed", "error": "BGM error"}

                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await generate_mix(
                        text="Hello world",
                        prompt="calm ambient",
                        db=mock_db,
                        current_user=mock_current_user,
                    )
                assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_generate_mix_success(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.music_mixer import generate_mix

        with patch("app.services.tts_pipeline.generate_tts_for_segment", new_callable=AsyncMock) as mock_tts:
            mock_tts.return_value = {
                "status": "success",
                "local_path": "/tmp/tts.mp3",
                "duration_seconds": 10.0,
            }

            with patch("app.services.suno_service.generate_music", new_callable=AsyncMock) as mock_bgm:
                mock_bgm.return_value = {
                    "status": "success",
                    "local_path": "/tmp/bgm.mp3",
                    "duration_seconds": 15.0,
                }

                with patch("app.services.ffmpeg_service.combine_audio_streams", new_callable=AsyncMock) as mock_combine:
                    mock_combine.return_value = "/tmp/mixed.mp3"

                    with patch("os.makedirs"):
                        with patch("asyncio.create_subprocess_exec") as mock_exec:
                            mock_exec.return_value = AsyncMock(
                                returncode=0,
                                communicate=AsyncMock(return_value=(b"10.0", b"")),
                            )

                            result = await generate_mix(
                                text="Hello world",
                                prompt="calm ambient",
                                db=mock_db,
                                current_user=mock_current_user,
                            )

                            assert result["status"] == "success"
                            assert "tts_path" in result
                            assert "bgm_path" in result
                            assert "output_path" in result