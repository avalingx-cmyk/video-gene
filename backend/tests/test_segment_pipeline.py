import pytest
from app.services.segment_pipeline import (
    validate_segment_prompt,
    validate_segment_duration,
    validate_narration_timing,
    validate_segment,
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    VIDEO_PROHIBITED_PATTERNS,
    TEXT_IN_VIDEO_ERROR,
)


class TestValidateSegmentPrompt:
    def test_valid_prompt_no_text(self):
        ok, msg = validate_segment_prompt("A cinematic shot of a sunset over mountains, golden hour lighting")
        assert ok is True
        assert msg == ""

    def test_invalid_prompt_contains_text(self):
        ok, msg = validate_segment_prompt("A video with title 'Hello' displayed")
        assert ok is False
        assert "text" in msg.lower() or "prohibited" in msg.lower()

    def test_invalid_prompt_contains_brand(self):
        ok, msg = validate_segment_prompt("Brand logo animation with company name")
        assert ok is False

    def test_invalid_prompt_contains_subtitle(self):
        ok, msg = validate_segment_prompt("Subtitle caption for the scene")
        assert ok is False

    def test_case_insensitive_detection(self):
        ok, msg = validate_segment_prompt("TEXT overlay with Title display")
        assert ok is False


class TestValidateSegmentDuration:
    def test_valid_duration(self):
        ok, msg = validate_segment_duration(10.0)
        assert ok is True

    def test_valid_min_duration(self):
        ok, msg = validate_segment_duration(MIN_DURATION_SECONDS)
        assert ok is True

    def test_valid_max_duration(self):
        ok, msg = validate_segment_duration(MAX_DURATION_SECONDS)
        assert ok is True

    def test_invalid_too_short(self):
        ok, msg = validate_segment_duration(2.0)
        assert ok is False
        assert "below minimum" in msg

    def test_invalid_too_long(self):
        ok, msg = validate_segment_duration(20.0)
        assert ok is False
        assert "exceeds maximum" in msg


class TestValidateNarrationTiming:
    def test_narration_fits_duration(self):
        text = "This is a short narration that should fit within the time."
        ok, msg = validate_narration_timing(text, 10.0)
        assert ok is True

    def test_narration_too_long(self):
        text = " ".join(["word"] * 500)
        ok, msg = validate_narration_timing(text, 5.0)
        assert ok is False
        assert "exceeds" in msg

    def test_narration_just_under_limit(self):
        text = " ".join(["word"] * 100)
        ok, msg = validate_narration_timing(text, 30.0)
        assert ok is True


class TestValidateSegment:
    def test_full_validation_valid(self):
        segment_data = {
            "video_prompt": "A beautiful sunset over the ocean",
            "duration_seconds": 10.0,
            "narration_text": "Today we explore the beauty of nature.",
        }
        is_valid, errors = validate_segment(segment_data)
        assert is_valid is True
        assert len(errors) == 0

    def test_full_validation_multiple_errors(self):
        segment_data = {
            "video_prompt": "Video with text title overlay",
            "duration_seconds": 3.0,
            "narration_text": " ".join(["word"] * 500),
        }
        is_valid, errors = validate_segment(segment_data)
        assert is_valid is False
        assert len(errors) >= 2

    def test_full_validation_prompt_only(self):
        segment_data = {
            "video_prompt": "A clean video with no text",
        }
        is_valid, errors = validate_segment(segment_data)
        assert is_valid is True


class TestVideoProhibitedPatterns:
    def test_key_patterns_exist(self):
        assert "title" in VIDEO_PROHIBITED_PATTERNS
        assert "subtitle" in VIDEO_PROHIBITED_PATTERNS
        assert "brand" in VIDEO_PROHIBITED_PATTERNS
        assert "logo" in VIDEO_PROHIBITED_PATTERNS

    def test_error_message_defined(self):
        assert TEXT_IN_VIDEO_ERROR is not None
        assert len(TEXT_IN_VIDEO_ERROR) > 0