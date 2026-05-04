import asyncio
import os
import subprocess
import pytest

pytestmark = pytest.mark.asyncio

HAVE_FFMPEG = os.system("which ffmpeg > /dev/null 2>&1") == 0

SKIP_MSG = "ffmpeg not available"


def _create_test_video(path: str, color: str = "black", duration: int = 3, width: int = 320, height: int = 240):
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d={duration}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100",
            "-shortest",
            "-c:v", "libx264", "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            path,
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg test video creation failed: {result.stderr.decode()[-500:]}")
    return path


@pytest.mark.skipif(not HAVE_FFMPEG, reason=SKIP_MSG)
class TestFFmpegIntegration:

    async def test_probe_duration(self, tmp_path):
        from app.services.ffmpeg_service import probe_duration

        src = str(tmp_path / "probe.mp4")
        _create_test_video(src, color="black", duration=5)

        dur = await probe_duration(src)
        assert dur > 4.5
        assert dur < 6.0

    async def test_get_video_info(self, tmp_path):
        from app.services.ffmpeg_service import get_video_info

        src = str(tmp_path / "info.mp4")
        _create_test_video(src, color="blue", duration=3)

        info = await get_video_info(src)
        assert info["width"] == 320
        assert info["height"] == 240
        assert info["has_audio"] is True
        assert info["duration"] > 2.5

    async def test_concat_single_file(self, tmp_path):
        from app.services.ffmpeg_service import concatenate_videos_with_transitions

        src = str(tmp_path / "src.mp4")
        out = str(tmp_path / "out.mp4")
        _create_test_video(src, color="blue", duration=3)

        result = await concatenate_videos_with_transitions([src], out)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    async def test_concat_two_files_with_xfade(self, tmp_path):
        from app.services.ffmpeg_service import concatenate_videos_with_transitions, probe_duration

        src1 = str(tmp_path / "src1.mp4")
        src2 = str(tmp_path / "src2.mp4")
        out = str(tmp_path / "out.mp4")
        _create_test_video(src1, color="red", duration=3)
        _create_test_video(src2, color="green", duration=3)

        result = await concatenate_videos_with_transitions(
            [src1, src2], out, transitions=["fade"], fade_duration=1.0
        )
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

        dur = await probe_duration(result)
        assert dur > 4.0

    async def test_concat_three_files_with_xfade_chain(self, tmp_path):
        from app.services.ffmpeg_service import concatenate_videos_with_transitions

        sources = []
        for i, color in enumerate(["red", "green", "blue"]):
            src = str(tmp_path / f"src{i}.mp4")
            _create_test_video(src, color=color, duration=3)
            sources.append(src)

        out = str(tmp_path / "out.mp4")
        result = await concatenate_videos_with_transitions(
            sources, out, transitions=["fade", "wipe"], fade_duration=1.0
        )
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    async def test_drawtext_overlay(self, tmp_path):
        from app.services.ffmpeg_service import add_text_overlay

        src = str(tmp_path / "src.mp4")
        out = str(tmp_path / "overlay.mp4")
        _create_test_video(src, color="black", duration=5)

        overlays = [{"text": "Hello", "font_size": 24, "x": "(w-text_w)/2", "y": "(h-text_h)/2", "start_time": 0, "end_time": 5}]
        result = await add_text_overlay(src, out, overlays, width=320, height=240)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    async def test_drawtext_anchor_overlay(self, tmp_path):
        from app.services.ffmpeg_service import add_text_overlay

        src = str(tmp_path / "src.mp4")
        out = str(tmp_path / "anchor.mp4")
        _create_test_video(src, color="black", duration=5)

        overlays = [{"text": "TOP", "font_size": 20, "anchor": "top_center", "start_time": 0, "end_time": 2}]
        result = await add_text_overlay(src, out, overlays, width=320, height=240)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    async def test_fade_in_out(self, tmp_path):
        from app.services.ffmpeg_service import apply_fade_in_out

        src = str(tmp_path / "src.mp4")
        out = str(tmp_path / "faded.mp4")
        _create_test_video(src, color="blue", duration=5)

        result = await apply_fade_in_out(src, out, fade_in_duration=0.5, fade_out_duration=0.5)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    async def test_validate_segments(self, tmp_path):
        from app.services.ffmpeg_service import validate_segments, SegmentSpec

        errors = validate_segments([])
        assert "No segments" in errors[0]

        errors = validate_segments([SegmentSpec(video_path="/nonexistent/file.mp4")])
        assert any("Missing" in e for e in errors)

    async def test_overlay_spec_anchor_resolution(self):
        from app.services.ffmpeg_service import OverlaySpec

        o = OverlaySpec(text="Test", anchor="bottom_center")
        x, y = o.resolve_position()
        assert x == "(w-text_w)/2"
        assert y == "(h-text_h)"

    async def test_segment_spec_defaults(self):
        from app.services.ffmpeg_service import SegmentSpec

        s = SegmentSpec(video_path="/tmp/test.mp4")
        assert s.transition == "fade"
        assert s.fade_in == 0.0
        assert s.fade_out == 0.0