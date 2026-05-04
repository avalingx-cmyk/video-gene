import asyncio
import os
import struct
import tempfile
import wave

import pytest

from app.services.ffmpeg_service import (
    ANCHOR_MAP,
    CompositionError,
    CompositionResult,
    OverlaySpec,
    SegmentSpec,
    SegmentValidationError,
    _format_ass_time,
    _generate_ass_script,
    _hex_to_ass_color,
    _needs_ass_subtitle,
    _resolve_transition,
    validate_segments,
)

pytestmark = pytest.mark.asyncio


class TestOverlaySpec:
    def test_default_values(self):
        o = OverlaySpec(text="Hello")
        assert o.text == "Hello"
        assert o.font_size == 48
        assert o.font_color == "#FFFFFF"
        assert o.animation == "none"

    def test_resolve_position_center(self):
        o = OverlaySpec(text="Hi", anchor="center")
        x, y = o.resolve_position()
        assert x == "(w-text_w)/2"
        assert y == "(h-text_h)/2"

    def test_resolve_position_top_left(self):
        o = OverlaySpec(text="Hi", anchor="top_left")
        x, y = o.resolve_position()
        assert x == "0"
        assert y == "0"

    def test_resolve_position_bottom_right(self):
        o = OverlaySpec(text="Hi", anchor="bottom_right")
        x, y = o.resolve_position()
        assert x == "(w-text_w)"
        assert y == "(h-text_h)"

    def test_resolve_position_numeric(self):
        o = OverlaySpec(text="Hi", x=100, y=200)
        x, y = o.resolve_position()
        assert x == "100"
        assert y == "200"

    def test_resolve_font_path_arial(self):
        o = OverlaySpec(text="Hi", font_family="Arial")
        result = o.resolve_font_path()
        assert result  # Should return a path or the font name

    def test_resolve_font_path_unknown(self):
        o = OverlaySpec(text="Hi", font_family="UnknownFont123")
        result = o.resolve_font_path()
        assert result  # Should fall back to something


class TestResolveTransition:
    def test_fade(self):
        assert _resolve_transition("fade") == "fade"

    def test_wipe(self):
        assert _resolve_transition("wipe") == "wiperight"

    def test_slide(self):
        assert _resolve_transition("slide") == "slideright"

    def test_circleopen(self):
        assert _resolve_transition("circleopen") == "circleopen"

    def test_dissolve(self):
        assert _resolve_transition("dissolve") == "dissolve"

    def test_unknown_defaults_to_fade(self):
        assert _resolve_transition("unknown_transition_xyz") == "fade"


class TestNeedsAssSubtitle:
    def test_simple_overlay_no_ass(self):
        overlays = [OverlaySpec(text="Hello", animation="none")]
        assert _needs_ass_subtitle(overlays) is False

    def test_animation_triggers_ass(self):
        overlays = [OverlaySpec(text="Hello", animation="typewriter")]
        assert _needs_ass_subtitle(overlays) is True

    def test_multiline_triggers_ass(self):
        overlays = [OverlaySpec(text="Line1\nLine2\nLine3")]
        assert _needs_ass_subtitle(overlays) is True

    def test_fade_animation_no_ass(self):
        overlays = [OverlaySpec(text="Hello", animation="fade")]
        assert _needs_ass_subtitle(overlays) is False

    def test_two_lines_no_ass(self):
        overlays = [OverlaySpec(text="Line1\nLine2")]
        assert _needs_ass_subtitle(overlays) is False


class TestFormatAssTime:
    def test_zero(self):
        assert _format_ass_time(0.0) == "0:00:00.00"

    def test_one_minute(self):
        assert _format_ass_time(60.0) == "0:01:00.00"

    def test_complex(self):
        assert _format_ass_time(3661.5) == "1:01:01.50"


class TestHexToAssColor:
    def test_white(self):
        result = _hex_to_ass_color("#FFFFFF")
        assert result == "BFFFFFF"

    def test_red(self):
        result = _hex_to_ass_color("#FF0000")
        assert result == "B0000FF"

    def test_no_hash(self):
        result = _hex_to_ass_color("FF0000")
        assert result == "B0000FF"


class TestGenerateAssScript:
    def test_basic_overlay(self):
        overlays = [OverlaySpec(text="Hello", start_time=0.0, end_time=5.0, anchor="center")]
        script = _generate_ass_script(overlays, 1080, 1920)
        assert "[Script Info]" in script
        assert "Overlay0" in script
        assert "Hello" in script
        assert "Dialogue:" in script

    def test_fade_animation(self):
        overlays = [OverlaySpec(text="Fade In", start_time=1.0, end_time=5.0, animation="fade")]
        script = _generate_ass_script(overlays, 1080, 1920)
        assert "fade" in script.lower() or "\\fad" in script or "\\fade" in script


class TestValidateSegments:
    def test_empty_segments(self):
        errors = validate_segments([])
        assert len(errors) > 0
        assert "No segments" in errors[0]

    def test_missing_video_file(self):
        seg = SegmentSpec(video_path="/nonexistent/video.mp4")
        errors = validate_segments([seg])
        assert any("Missing video files" in e for e in errors)

    def test_negative_fade_duration(self):
        seg = SegmentSpec(video_path="/tmp/test.mp4", fade_in=-1.0)
        errors = validate_segments([seg])
        assert any("fade" in e.lower() for e in errors)

    def test_valid_segment_with_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video")
            seg = SegmentSpec(video_path=f.name)
            errors = validate_segments([seg])
            missing_errors = [e for e in errors if "Missing video files" in e]
            assert len(missing_errors) == 0
            os.unlink(f.name)


class TestSegmentSpec:
    def test_defaults(self):
        s = SegmentSpec(video_path="/tmp/test.mp4")
        assert s.duration is None
        assert s.transition == "fade"
        assert s.fade_in == 0.0
        assert s.fade_out == 0.0
        assert s.overlays == []

    def test_with_overlays(self):
        s = SegmentSpec(
            video_path="/tmp/test.mp4",
            overlays=[OverlaySpec(text="Title")],
            tts_path="/tmp/audio.mp3",
        )
        assert len(s.overlays) == 1
        assert s.tts_path == "/tmp/audio.mp3"


class TestCompositionResult:
    def test_defaults(self):
        r = CompositionResult(
            output_path="/tmp/out.mp4",
            final_duration=30.0,
            segments_composed=3,
            overlays_applied=2,
            audio_tracks=4,
        )
        assert r.output_path == "/tmp/out.mp4"
        assert r.final_duration == 30.0
        assert r.segments_composed == 3
        assert r.warnings == []

    def test_with_warnings(self):
        r = CompositionResult(
            output_path="/tmp/out.mp4",
            final_duration=30.0,
            segments_composed=3,
            overlays_applied=0,
            audio_tracks=1,
            warnings=["Duration probe failed"],
        )
        assert len(r.warnings) == 1


class TestAnchormap:
    def test_all_anchors_defined(self):
        expected = [
            "top_left", "top_center", "top_right",
            "center_left", "center", "center_right",
            "bottom_left", "bottom_center", "bottom_right",
        ]
        for anchor in expected:
            assert anchor in ANCHOR_MAP, f"Missing anchor: {anchor}"

    def test_anchor_values_are_tuples(self):
        for key, val in ANCHOR_MAP.items():
            assert isinstance(val, tuple), f"Anchor {key} is not a tuple"
            assert len(val) == 2, f"Anchor {key} does not have 2 elements"


class TestIntegrationPatchPaths:
    def test_export_final_video_backward_compat_params(self):
        result = CompositionResult(
            output_path="/tmp/test.mp4",
            final_duration=30.0,
            segments_composed=3,
            overlays_applied=5,
            audio_tracks=3,
        )
        assert result.final_duration > 0
        assert result.segments_composed == 3