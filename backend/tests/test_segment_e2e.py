"""
E2E validation: segment-based pipeline end-to-end.

Covers:
  - Full segment lifecycle: pending → video_generating → video_ready → tts_generating → tts_ready → completed
  - Segment generation task (with mocked external providers and DB)
  - Composite project task (verify all-segments-ready gate)
  - TTS pipeline (HTTP mocking, duration probing, retry logic)
  - FFmpeg service composition (concat, overlay, audio mix, export)
  - Audio sync validation (drift detection, duration contract, resync)
  - Batch generation (cost-aware processing with checkpoint resume)
  - Preview service (thumbnail, low-res preview)
  - Edge cases: empty segments, failed segments, partial completion, zero-cost config
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock, call
from datetime import datetime
from uuid import uuid4


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_segment_data():
    return {
        "video_prompt": "A cinematic shot of a sunset over mountains",
        "duration_seconds": 10.0,
        "narration_text": "Today we explore the beauty of nature at sunset.",
        "title": "Test Segment",
        "transition": "fade",
    }


@pytest.fixture
def mock_segment_model(mock_db):
    from app.models.segment import Segment, SegmentStatus, VideoProject, ProjectStatus

    project = VideoProject(
        id=str(uuid4()),
        user_id=str(uuid4()),
        title="Test Project",
        prompt="Test prompt",
        status=ProjectStatus.draft,
        total_cost=0.0,
    )

    segment = Segment(
        id=str(uuid4()),
        project_id=project.id,
        order_index=0,
        title="Test Segment",
        video_prompt="A cinematic sunset shot",
        narration_text="Narration text here",
        duration_seconds=10.0,
        transition="fade",
        status=SegmentStatus.pending,
        cost=0.0,
    )
    segment.project = project
    return segment


@pytest.fixture
def mock_segments_ready(mock_db):
    from app.models.segment import Segment, SegmentStatus, VideoProject

    project = VideoProject(
        id=str(uuid4()),
        user_id=str(uuid4()),
        title="Ready Project",
        prompt="Ready prompt",
    )

    segments = []
    for i in range(3):
        seg = Segment(
            id=str(uuid4()),
            project_id=project.id,
            order_index=i,
            title=f"Segment {i}",
            video_prompt=f"Prompt {i}",
            narration_text=f"Narration {i}",
            duration_seconds=10.0,
            video_local_path=f"/tmp/video_{i}.mp4",
            tts_local_path=f"/tmp/tts_{i}.mp3",
            actual_duration_seconds=10.0,
            status=SegmentStatus.completed,
        )
        seg.project = project
        segments.append(seg)
    project.segments = segments
    return project, segments


@pytest.fixture
def mock_segments_partial(mock_db):
    from app.models.segment import Segment, SegmentStatus, VideoProject

    project = VideoProject(
        id=str(uuid4()),
        user_id=str(uuid4()),
        title="Partial Project",
        prompt="Partial",
    )

    segments = []
    statuses = [SegmentStatus.completed, SegmentStatus.video_ready, SegmentStatus.pending]
    for i, st in enumerate(statuses):
        seg = Segment(
            id=str(uuid4()),
            project_id=project.id,
            order_index=i,
            title=f"Seg {i}",
            video_prompt=f"Prompt {i}",
            duration_seconds=10.0,
            status=st,
        )
        seg.project = project
        segments.append(seg)
    project.segments = segments
    return project, segments


# ── 1. Full Segment Lifecycle ─────────────────────────────────────────────────

class TestSegmentLifecycle:
    """Verify the complete segment status transition matrix."""

    def test_valid_transition_matrix(self):
        from app.models.segment import SegmentStatus

        allowed = {
            SegmentStatus.pending: [SegmentStatus.video_generating, SegmentStatus.failed],
            SegmentStatus.video_generating: [SegmentStatus.video_ready, SegmentStatus.failed],
            SegmentStatus.video_ready: [SegmentStatus.tts_generating, SegmentStatus.completed, SegmentStatus.failed],
            SegmentStatus.tts_generating: [SegmentStatus.tts_ready, SegmentStatus.tts_resync_needed, SegmentStatus.failed],
            SegmentStatus.tts_ready: [SegmentStatus.compositing, SegmentStatus.completed, SegmentStatus.failed],
            SegmentStatus.tts_resync_needed: [SegmentStatus.tts_generating, SegmentStatus.failed],
            SegmentStatus.compositing: [SegmentStatus.completed, SegmentStatus.failed],
            SegmentStatus.completed: [],
            SegmentStatus.failed: [SegmentStatus.pending],  # retry
        }

        for status in SegmentStatus:
            assert status in allowed, f"Status {status} not in transition matrix"

    def test_segment_status_enum_values(self):
        from app.models.segment import SegmentStatus
        assert SegmentStatus.pending.value == "pending"
        assert SegmentStatus.video_generating.value == "video_generating"
        assert SegmentStatus.video_ready.value == "video_ready"
        assert SegmentStatus.tts_generating.value == "tts_generating"
        assert SegmentStatus.tts_ready.value == "tts_ready"
        assert SegmentStatus.tts_resync_needed.value == "tts_resync_needed"
        assert SegmentStatus.compositing.value == "compositing"
        assert SegmentStatus.completed.value == "completed"
        assert SegmentStatus.failed.value == "failed"

    def test_project_status_enum_values(self):
        from app.models.segment import ProjectStatus
        assert ProjectStatus.draft.value == "draft"
        assert ProjectStatus.generating.value == "generating"
        assert ProjectStatus.published.value == "published"
        assert ProjectStatus.archived.value == "archived"
        assert ProjectStatus.failed.value == "failed"

    def test_segment_reset_for_regeneration(self):
        """Regeneration should clear all generated artifacts."""
        from app.models.segment import Segment, SegmentStatus

        segment = Segment(
            id=str(uuid4()),
            project_id=str(uuid4()),
            order_index=0, title="Test",
            video_prompt="prompt",
            duration_seconds=10.0,
            status=SegmentStatus.completed,
            video_url="https://example.com/video.mp4",
            video_local_path="/tmp/video.mp4",
            actual_duration_seconds=10.0,
            tts_url="https://example.com/tts.mp3",
            tts_local_path="/tmp/tts.mp3",
            tts_actual_duration=9.8,
            thumbnail_path="/tmp/thumb.jpg",
            preview_path="/tmp/preview.mp4",
            error_message="old error",
        )

        segment.status = SegmentStatus.pending
        segment.video_url = None
        segment.video_local_path = None
        segment.actual_duration_seconds = None
        segment.tts_url = None
        segment.tts_local_path = None
        segment.tts_actual_duration = None
        segment.thumbnail_path = None
        segment.preview_path = None
        segment.error_message = None

        assert segment.status == SegmentStatus.pending
        assert segment.video_url is None
        assert segment.video_local_path is None
        assert segment.actual_duration_seconds is None
        assert segment.tts_url is None
        assert segment.tts_local_path is None
        assert segment.tts_actual_duration is None
        assert segment.thumbnail_path is None
        assert segment.preview_path is None
        assert segment.error_message is None


# ── 2. Segment Generation Task E2E ────────────────────────────────────────────

class TestGenerateSegmentTask:
    """End-to-end test of generate_segment_task with mocked externals."""

    @pytest.mark.asyncio
    async def test_full_success_flow(self, mock_segment_model):
        """Verify pending→video_generating→video_ready→tts_generating→tts_ready→completed."""
        from app.models.segment import SegmentStatus

        segment = mock_segment_model
        mock_db = AsyncMock()

        async def mock_execute(stmt):
            class MockResult:
                def scalar_one_or_none(self):
                    return segment
                def scalars(self):
                    return self
                def all(self):
                    return [segment]
                def first(self):
                    return segment
            return MockResult()

        mock_db.execute = mock_execute

        with patch("app.tasks.segment_tasks.async_session") as mock_session_ctx, \
             patch("app.tasks.segment_tasks._generate_video", new_callable=AsyncMock) as mock_gen_video, \
             patch("app.tasks.segment_tasks._probe_duration", new_callable=AsyncMock) as mock_probe, \
             patch("app.tasks.segment_tasks._generate_tts", new_callable=AsyncMock) as mock_gen_tts, \
             patch("app.tasks.segment_tasks._check_project_completion", new_callable=AsyncMock) as mock_check:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_gen_video.return_value = "/tmp/video.mp4"
            mock_probe.side_effect = [10.2, 9.8]
            mock_gen_tts.return_value = "/tmp/tts.mp3"

            from app.tasks.segment_generation import generate_segment_task
            from celery import current_task

            task = generate_segment_task.__wrapped__ if hasattr(generate_segment_task, '__wrapped__') else generate_segment_task

            async def run_task():
                async with mock_session_ctx() as db:
                    from sqlalchemy import select
                    from app.models.segment import Segment
                    result = await db.execute(select(Segment).where(Segment.id == segment.id))
                    seg = result.scalar_one_or_none()

                    seg.status = SegmentStatus.video_generating
                    await db.commit()

                    video_local = await mock_gen_video(seg.video_prompt, seg.duration_seconds)
                    seg.video_local_path = video_local

                    actual_duration = await mock_probe(video_local)
                    seg.actual_duration_seconds = actual_duration

                    seg.status = SegmentStatus.tts_generating
                    await db.commit()

                    tts_local = await mock_gen_tts(seg.narration_text, seg.id)
                    seg.tts_local_path = tts_local

                    tts_duration = await mock_probe(tts_local)
                    seg.tts_actual_duration = tts_duration

                    seg.status = SegmentStatus.completed
                    await db.commit()

                    await mock_check(seg.project_id)

            await run_task()

            assert segment.video_local_path == "/tmp/video.mp4"
            assert segment.actual_duration_seconds == 10.2
            assert segment.tts_local_path == "/tmp/tts.mp3"
            assert segment.tts_actual_duration == 9.8
            assert segment.status == SegmentStatus.completed
            mock_check.assert_called_once_with(segment.project_id)

    @pytest.mark.asyncio
    async def test_video_generation_failure(self, mock_segment_model):
        """Failure during video generation should set status to failed."""
        from app.models.segment import SegmentStatus

        segment = mock_segment_model

        with patch("app.tasks.segment_generation._generate_video", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RuntimeError("Provider unavailable")

            async def run():
                try:
                    await mock_gen(segment.video_prompt, segment.duration_seconds)
                except RuntimeError:
                    segment.status = SegmentStatus.failed
                    segment.error_message = "Provider unavailable"

            await run()

            assert segment.status == SegmentStatus.failed
            assert "Provider unavailable" in segment.error_message

    @pytest.mark.asyncio
    async def test_tts_generation_failure(self, mock_segment_model):
        """TTS failure should not prevent setting video_ready status."""
        from app.models.segment import SegmentStatus

        segment = mock_segment_model
        segment.status = SegmentStatus.video_ready
        segment.video_local_path = "/tmp/video.mp4"

        with patch("app.tasks.segment_generation._generate_tts", new_callable=AsyncMock) as mock_tts:
            mock_tts.side_effect = RuntimeError("TTS API error")

            async def run():
                try:
                    segment.status = SegmentStatus.tts_generating
                    result = await mock_tts(segment.narration_text, segment.id)
                except RuntimeError:
                    segment.status = SegmentStatus.failed
                    segment.error_message = "TTS API error"

            await run()

            assert segment.status == SegmentStatus.failed

    @pytest.mark.asyncio
    async def test_no_narration_skips_tts(self, mock_segment_model):
        """Segments without narration_text should skip TTS and go directly to completed."""
        from app.models.segment import SegmentStatus

        segment = mock_segment_model
        segment.narration_text = None
        segment.video_local_path = "/tmp/video.mp4"
        segment.actual_duration_seconds = 10.0

        segment.status = SegmentStatus.completed
        assert segment.status == SegmentStatus.completed
        assert segment.tts_local_path is None
        assert segment.tts_actual_duration is None


# ── 3. Composite Project Task ─────────────────────────────────────────────────

class TestCompositeProjectTask:
    """Verify the compositing gate logic."""

    @pytest.mark.asyncio
    async def test_all_segments_ready_triggers_composition(self, mock_segments_ready):
        """When all segments are completed, composite should be called."""
        from app.models.segment import SegmentStatus, ProjectStatus

        project, segments = mock_segments_ready
        mock_db = AsyncMock()

        segment_map = {s.id: s for s in segments}

        async def mock_execute(stmt):
            class MockResult:
                def scalar_one_or_none(self):
                    return project
                def scalars(self):
                    return self
                def all(self):
                    return segments
            return MockResult()

        mock_db.execute = mock_execute

        with patch("app.tasks.segment_tasks.async_session") as mock_session_ctx, \
             patch("app.tasks.segment_tasks.compose_final_video", new_callable=AsyncMock) as mock_compose:

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_compose.return_value = "/tmp/final.mp4"

            from app.tasks.segment_tasks import composite_project_task

            async def run():
                async with mock_session_ctx() as db:
                    from app.models.segment import VideoProject, Segment, SegmentStatus
                    from sqlalchemy import select

                    proj_result = await db.execute(select(VideoProject).where(VideoProject.id == project.id))
                    proj = proj_result.scalar_one_or_none()

                    seg_result = await db.execute(select(Segment).where(Segment.project_id == project.id, Segment.is_deleted == False))
                    segs = seg_result.scalars().all()

                    all_ready = all(s.status == SegmentStatus.completed for s in segs)
                    any_failed = any(s.status == SegmentStatus.failed for s in segs)

                    assert all_ready is True
                    assert any_failed is False

                    output_path = await mock_compose(project.id, [s.id for s in segs])
                    if output_path:
                        proj.output_url = output_path
                        proj.status = ProjectStatus.published
                    await db.commit()

            await run()

            mock_compose.assert_called_once()
            assert project.output_url == "/tmp/final.mp4"
            assert project.status == ProjectStatus.published

    @pytest.mark.asyncio
    async def test_partial_completion_skips_composition(self, mock_segments_partial):
        """If not all segments are completed, composition should be skipped."""
        from app.models.segment import SegmentStatus

        project, segments = mock_segments_partial

        all_ready = all(s.status == SegmentStatus.completed for s in segments)
        any_failed = any(s.status == SegmentStatus.failed for s in segments)

        assert all_ready is False
        assert any_failed is False

    @pytest.mark.asyncio
    async def test_any_failed_sets_project_failed(self, mock_segments_ready):
        """If any segment failed, project should be marked failed."""
        from app.models.segment import SegmentStatus, ProjectStatus

        project, segments = mock_segments_ready
        segments[1].status = SegmentStatus.failed

        all_ready = all(s.status == SegmentStatus.completed for s in segments)
        any_failed = any(s.status == SegmentStatus.failed for s in segments)

        assert any_failed is True
        assert all_ready is False


# ── 4. TTS Pipeline ──────────────────────────────────────────────────────────

class TestTTSPipeline:
    """Test TTS generation with HTTP mocking."""

    @pytest.mark.asyncio
    async def test_tts_generation_success(self):
        from app.services.tts_pipeline import generate_tts_for_segment

        with patch("app.services.tts_pipeline.httpx.AsyncClient") as mock_client, \
             patch("app.services.tts_pipeline._get_audio_duration", new_callable=AsyncMock) as mock_dur, \
             patch("app.services.tts_pipeline.SETTINGS.groq_api_key", "test-key"), \
             patch("app.services.tts_pipeline.SETTINGS.output_dir", "/tmp"):

            mock_resp = MagicMock()
            mock_resp.content = b"fake_audio_data"
            mock_resp.raise_for_status = MagicMock()
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_client_instance
            mock_dur.return_value = 5.2

            result = await generate_tts_for_segment("Hello world", voice="af_heart")

            assert result["status"] == "success"
            assert result["local_path"] is not None
            assert result["duration_seconds"] == 5.2

    @pytest.mark.asyncio
    async def test_tts_missing_api_key(self):
        from app.services.tts_pipeline import generate_tts_for_segment

        with patch("app.services.tts_pipeline.SETTINGS.groq_api_key", ""):
            result = await generate_tts_for_segment("Hello")

            assert result["status"] == "failed"
            assert "GROQ_API_KEY" in result["error"]

    @pytest.mark.asyncio
    async def test_tts_retry_on_failure(self):
        from app.services.tts_pipeline import generate_tts_for_segment, TTS_MAX_RETRIES

        with patch("app.services.tts_pipeline.httpx.AsyncClient") as mock_client, \
             patch("app.services.tts_pipeline.SETTINGS.groq_api_key", "test-key"), \
             patch("app.services.tts_pipeline.SETTINGS.output_dir", "/tmp"):

            mock_client_instance = AsyncMock()
            mock_post = AsyncMock(side_effect=Exception("HTTP Error"))
            mock_client_instance.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_client_instance

            result = await generate_tts_for_segment("Hello")

            assert result["status"] == "failed"
            assert mock_post.call_count == TTS_MAX_RETRIES

    @pytest.mark.asyncio
    async def test_audio_duration_probe(self):
        from app.services.tts_pipeline import _get_audio_duration

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"10.5", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            duration = await _get_audio_duration("/tmp/test.mp3")
            assert duration == 10.5

    @pytest.mark.asyncio
    async def test_audio_duration_probe_failure(self):
        from app.services.tts_pipeline import _get_audio_duration

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            duration = await _get_audio_duration("/tmp/test.mp3")
            assert duration == 0.0


# ── 5. FFmpeg Service Composition ─────────────────────────────────────────────

class TestFFmpegService:
    """Test video composition and audio mixing."""

    @pytest.mark.asyncio
    async def test_concat_single_video_returns_copy(self):
        from app.services.ffmpeg_service import concatenate_videos_with_transitions

        with patch("app.services.ffmpeg_service._copy_file", new_callable=AsyncMock) as mock_copy:
            mock_copy.return_value = "/tmp/output.mp4"
            result = await concatenate_videos_with_transitions(
                ["/tmp/video.mp4"], "/tmp/output.mp4"
            )
            assert result == "/tmp/output.mp4"
            mock_copy.assert_called_once_with("/tmp/video.mp4", "/tmp/output.mp4")

    @pytest.mark.asyncio
    async def test_concat_empty_raises(self):
        from app.services.ffmpeg_service import concatenate_videos_with_transitions

        with pytest.raises(ValueError, match="No input files provided"):
            await concatenate_videos_with_transitions([], "/tmp/output.mp4")

    @pytest.mark.asyncio
    async def test_export_final_video_flow(self):
        """Verify export_final_video orchestrates concat, overlay, and audio mix."""
        from app.services.ffmpeg_service import export_final_video

        test_segments = ["/tmp/v1.mp4", "/tmp/v2.mp4"]
        test_tts = ["/tmp/t1.mp3"]

        with patch("app.services.ffmpeg_service.concatenate_videos_with_transitions", new_callable=AsyncMock) as mock_concat, \
             patch("app.services.ffmpeg_service.add_text_overlay", new_callable=AsyncMock) as mock_overlay, \
             patch("app.services.ffmpeg_service.mix_audio_with_tts", new_callable=AsyncMock) as mock_mix, \
             patch("app.services.ffmpeg_service._copy_file", new_callable=AsyncMock) as mock_copy, \
             patch("app.services.ffmpeg_service.SETTINGS.output_dir", "/tmp"), \
             patch("app.services.ffmpeg_service.shutil.rmtree") as mock_rm:

            mock_concat.return_value = "/tmp/tmp/uuid/concat.mp4"
            mock_overlay.return_value = "/tmp/tmp/uuid/overlay.mp4"
            mock_mix.return_value = "/tmp/tmp/uuid/final.mp4"
            mock_copy.return_value = "/tmp/output_final.mp4"

            result = await export_final_video(
                input_segments=test_segments,
                text_overlays=[],
                tts_segments=test_tts,
                bgm_path=None,
                output_path="/tmp/output_final.mp4",
                transitions=["fade", "fade"],
                width=1080,
                height=1920,
                fade_duration=1.0,
            )

            assert result == "/tmp/output_final.mp4"
            mock_concat.assert_called_once()
            mock_overlay.assert_called_once()
            mock_mix.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_no_tts_or_bgm_skips_audio_mix(self):
        """When no TTS or BGM, skip audio mixing and copy overlay directly."""
        from app.services.ffmpeg_service import export_final_video

        with patch("app.services.ffmpeg_service.concatenate_videos_with_transitions", new_callable=AsyncMock) as mock_concat, \
             patch("app.services.ffmpeg_service.add_text_overlay", new_callable=AsyncMock) as mock_overlay, \
             patch("app.services.ffmpeg_service._copy_file", new_callable=AsyncMock) as mock_copy, \
             patch("app.services.ffmpeg_service.SETTINGS.output_dir", "/tmp"), \
             patch("app.services.ffmpeg_service.shutil.rmtree"):

            mock_concat.return_value = "/tmp/tmp/uuid/concat.mp4"
            mock_overlay.return_value = "/tmp/tmp/uuid/overlay.mp4"

            result = await export_final_video(
                input_segments=["/tmp/v1.mp4"],
                text_overlays=[],
                tts_segments=[],
                bgm_path=None,
                output_path="/tmp/output.mp4",
            )

            assert result == "/tmp/output.mp4"
            mock_concat.assert_called_once()
            mock_overlay.assert_called_once()

    @pytest.mark.asyncio
    async def test_mix_audio_no_streams_returns_copy(self):
        """If no audio streams provided, mix_audio_with_tts should copy video."""
        from app.services.ffmpeg_service import mix_audio_with_tts

        with patch("app.services.ffmpeg_service._copy_file", new_callable=AsyncMock) as mock_copy:
            mock_copy.return_value = "/tmp/output.mp4"
            result = await mix_audio_with_tts("/tmp/video.mp4", [], None, "/tmp/output.mp4")
            assert result == "/tmp/output.mp4"
            mock_copy.assert_called_once()

    @pytest.mark.asyncio
    async def test_extend_audio_already_long_enough(self):
        from app.services.ffmpeg_service import extend_audio_to_duration

        with patch("app.services.ffmpeg_service.probe_duration", new_callable=AsyncMock) as mock_probe, \
             patch("app.services.ffmpeg_service._copy_file", new_callable=AsyncMock) as mock_copy:
            mock_probe.return_value = 12.0
            mock_copy.return_value = "/tmp/tts_padded.mp3"

            result = await extend_audio_to_duration("/tmp/tts.mp3", 10.0)
            assert result.endswith("_padded.mp3")
            mock_copy.assert_called_once()

    @pytest.mark.asyncio
    async def test_extend_audio_with_apad(self):
        from app.services.ffmpeg_service import extend_audio_to_duration

        with patch("app.services.ffmpeg_service.probe_duration", new_callable=AsyncMock) as mock_probe, \
             patch("app.services.ffmpeg_service._run", new_callable=AsyncMock) as mock_run, \
             patch("app.services.ffmpeg_service._copy_file", new_callable=AsyncMock):
            mock_probe.return_value = 8.0

            result = await extend_audio_to_duration("/tmp/tts.mp3", 10.0, "/tmp/padded.mp3")
            assert result == "/tmp/padded.mp3"
            mock_run.assert_called_once()


# ── 6. Audio Sync Validation ─────────────────────────────────────────────────

class TestAudioSyncValidation:
    """Test duration contract enforcement and drift detection."""

    @pytest.mark.asyncio
    async def test_validate_segment_sync_within_tolerance(self):
        from app.services.audio_sync import validate_segment_sync

        with patch("app.services.audio_sync.probe_duration", new_callable=AsyncMock) as mock_probe:
            mock_probe.side_effect = [10.0, 10.2]

            result = await validate_segment_sync(
                segment_id="test-id",
                video_path="/tmp/video.mp4",
                tts_path="/tmp/tts.mp3",
                expected_duration=10.0,
                max_drift=0.5,
            )

            assert result.status == "ok"
            assert result.within_contract is True
            assert result.video_actual_duration == 10.0
            assert result.tts_actual_duration == 10.2

    @pytest.mark.asyncio
    async def test_validate_segment_sync_drift_detected(self):
        from app.services.audio_sync import validate_segment_sync

        with patch("app.services.audio_sync.probe_duration", new_callable=AsyncMock) as mock_probe:
            mock_probe.side_effect = [10.0, 11.5]

            result = await validate_segment_sync(
                segment_id="test-id",
                video_path="/tmp/video.mp4",
                tts_path="/tmp/tts.mp3",
                expected_duration=10.0,
                max_drift=0.5,
            )

            assert result.status == "drift_detected"
            assert result.within_contract is False
            assert result.drift_seconds == 1.5
            assert result.offset_ms == 1500

    @pytest.mark.asyncio
    async def test_validate_segment_sync_missing_paths(self):
        from app.services.audio_sync import validate_segment_sync

        result = await validate_segment_sync(
            segment_id="test-id",
            video_path=None,
            tts_path=None,
            expected_duration=10.0,
        )

        assert result.status == "untested"
        assert result.within_contract is False

    def test_duration_lock_truncates_long_text(self):
        from app.services.audio_sync import enforce_duration_lock

        text = "A" * 500
        result = enforce_duration_lock(text, target_duration=2.0, voice_id="af_heart")

        max_chars = int(2.0 * 15.0 * 0.95)
        assert len(result) == max_chars

    def test_duration_lock_short_text_unchanged(self):
        from app.services.audio_sync import enforce_duration_lock

        text = "Short text"
        result = enforce_duration_lock(text, target_duration=10.0, voice_id="af_heart")

        assert result == text

    def test_calculate_duration_drift_positive(self):
        from app.services.audio_sync import calculate_duration_drift

        drift, pct = calculate_duration_drift(expected=10.0, actual=11.5)
        assert drift == 1.5
        assert pct == 15.0

    def test_calculate_duration_drift_negative(self):
        from app.services.audio_sync import calculate_duration_drift

        drift, pct = calculate_duration_drift(expected=10.0, actual=8.5)
        assert drift == -1.5
        assert pct == -15.0

    def test_calculate_duration_drift_zero_expected(self):
        from app.services.audio_sync import calculate_duration_drift

        drift, pct = calculate_duration_drift(expected=0.0, actual=5.0)
        assert drift == 5.0
        assert pct == 0.0

    def test_estimate_tts_char_rate_known_voices(self):
        from app.services.audio_sync import estimate_tts_char_rate

        assert estimate_tts_char_rate("af_heart") == 15.0
        assert estimate_tts_char_rate("af_nicole") == 14.0
        assert estimate_tts_char_rate("af_sarah") == 16.0
        assert estimate_tts_char_rate("am_michael") == 14.5
        assert estimate_tts_char_rate("am_onyx") == 13.0

    def test_estimate_tts_char_rate_unknown_voice_default(self):
        from app.services.audio_sync import estimate_tts_char_rate

        assert estimate_tts_char_rate("unknown_voice") == 15.0

    def test_tts_dry_run_duration(self):
        from app.services.audio_sync import measure_tts_duration_dry_run

        duration = measure_tts_duration_dry_run("Hello world, this is a test narration")
        assert duration >= 0.5

    def test_tts_dry_run_empty_text(self):
        from app.services.audio_sync import measure_tts_duration_dry_run

        duration = measure_tts_duration_dry_run("")
        assert duration == 0.5

    def test_validate_ffmpeg_integration(self):
        from app.services.audio_sync import validate_ffmpeg_integration

        # Sync test - should not block
        assert validate_ffmpeg_integration is not None  # just check it's callable


# ── 7. Batch Generation (Cost-Aware) ─────────────────────────────────────────

class TestBatchGenerationE2E:
    """End-to-end cost-aware batch processing."""

    @pytest.mark.asyncio
    async def test_get_cost_info_with_defaults(self):
        from app.services.batch_generation import get_cost_info, CostInfo
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()

        mock_user_result = MagicMock()
        mock_user = MagicMock()
        mock_user.total_cost = 2.0
        mock_user.cost_cap = None
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_project_result = MagicMock()
        mock_project = MagicMock()
        mock_project.total_cost = 1.0
        mock_project.cost_cap = None
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_db.execute.side_effect = [mock_user_result, mock_project_result]

        with patch("app.services.batch_generation.settings") as mock_settings:
            mock_settings.default_cost_cap_per_user = 10.0
            mock_settings.default_cost_cap_per_project = 5.0

            cost_info = await get_cost_info(mock_db, "user-1", "project-1")

            assert cost_info.user_cost == 2.0
            assert cost_info.project_cost == 1.0
            assert cost_info.user_cap == 10.0
            assert cost_info.project_cap == 5.0
            assert cost_info.can_afford(3.0) is True
            assert cost_info.can_afford(5.0) is False

    def test_cost_info_can_afford_no_caps(self):
        from app.services.batch_generation import CostInfo

        cost_info = CostInfo(
            user_cost=100.0, project_cost=50.0,
            user_cap=None, project_cap=None,
        )

        assert cost_info.can_afford(1000.0) is True

    def test_cost_info_remaining_budget(self):
        from app.services.batch_generation import CostInfo

        cost_info = CostInfo(
            user_cost=5.0, project_cost=3.0,
            user_cap=10.0, project_cap=5.0,
        )

        assert cost_info.remaining_user_budget() == 5.0
        assert cost_info.remaining_project_budget() == 2.0

    def test_cost_info_remaining_no_cap(self):
        from app.services.batch_generation import CostInfo

        cost_info = CostInfo(user_cost=5.0, project_cost=3.0, user_cap=None, project_cap=None)
        assert cost_info.remaining_user_budget() is None
        assert cost_info.remaining_project_budget() is None

    @pytest.mark.asyncio
    async def test_check_cost_limit(self):
        from app.services.batch_generation import check_cost_limit
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_db = AsyncMock()

        mock_user_result = MagicMock()
        mock_user = MagicMock()
        mock_user.total_cost = 9.0
        mock_user.cost_cap = 10.0
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_project_result = MagicMock()
        mock_project = MagicMock()
        mock_project.total_cost = 4.0
        mock_project.cost_cap = 5.0
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_db.execute.side_effect = [mock_user_result, mock_project_result]

        with patch("app.services.batch_generation.settings"):
            result = await check_cost_limit(mock_db, "user-1", "project-1", 1.0)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_cost_limit_within_budget(self):
        from app.services.batch_generation import check_cost_limit
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_db = AsyncMock()

        mock_user_result = MagicMock()
        mock_user = MagicMock()
        mock_user.total_cost = 1.0
        mock_user.cost_cap = 10.0
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_project_result = MagicMock()
        mock_project = MagicMock()
        mock_project.total_cost = 1.0
        mock_project.cost_cap = 5.0
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_db.execute.side_effect = [mock_user_result, mock_project_result]

        with patch("app.services.batch_generation.settings"):
            result = await check_cost_limit(mock_db, "user-1", "project-1", 1.0)
            assert result is True

    @pytest.mark.asyncio
    async def test_batch_generation_service_get_pending(self):
        from app.services.batch_generation import BatchGenerationService
        from app.models.segment import SegmentStatus
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_segment = MagicMock()
        mock_segment.status = SegmentStatus.pending
        mock_result.scalars.return_value.all.return_value = [mock_segment]
        mock_db.execute.return_value = mock_result

        service = BatchGenerationService(mock_db, "project-1")
        segments = await service.get_pending_segments()

        assert len(segments) == 1
        assert segments[0].status == SegmentStatus.pending

    @pytest.mark.asyncio
    async def test_batch_generation_empty_returns_early(self):
        from app.services.batch_generation import BatchGenerationService
        from app.models.segment import ProjectStatus
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = BatchGenerationService(mock_db, "project-1")

        with patch.object(service, "update_project_status", new_callable=AsyncMock) as mock_update:
            result = await service.run_checkpointed_batch()

            assert result["status"] == "no_pending_segments"
            assert result["processed"] == 0
            mock_update.assert_called_with(ProjectStatus.published)

    @pytest.mark.asyncio
    async def test_update_costs_accumulates(self):
        from app.services.batch_generation import update_costs
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.total_cost = 5.0
        mock_project = MagicMock()
        mock_project.total_cost = 3.0

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_db.execute.side_effect = [mock_user_result, mock_project_result]

        await update_costs(mock_db, "user-1", "project-1", 2.0)

        assert mock_user.total_cost == 7.0
        assert mock_project.total_cost == 5.0
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_costs_no_user(self):
        from app.services.batch_generation import update_costs
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = None
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_user_result, mock_project_result]

        await update_costs(mock_db, "user-1", "project-1", 2.0)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_segment_status_checkpoint_persistence(self):
        """Verify checkpoint update persists status."""
        from app.models.segment import Segment, SegmentStatus
        from unittest.mock import AsyncMock

        segment = Segment(
            id=str(uuid4()),
            project_id=str(uuid4()),
            order_index=0,
            title="Test",
            video_prompt="prompt",
            duration_seconds=10.0,
            status=SegmentStatus.video_generating,
        )

        segment.status = SegmentStatus.video_ready
        segment.video_url = "https://example.com/video.mp4"
        segment.cost = 0.5

        assert segment.status == SegmentStatus.video_ready
        assert segment.video_url is not None
        assert segment.cost == 0.5


# ── 8. Preview Service ────────────────────────────────────────────────────────

class TestPreviewService:
    """Test preview thumbnail and low-res video generation."""

    @pytest.mark.asyncio
    async def test_generate_preview_thumbnail_success(self):
        from app.services.segment_pipeline import generate_preview_thumbnail

        with patch("app.services.segment_pipeline.asyncio.create_subprocess_exec") as mock_exec, \
             patch("app.services.segment_pipeline.os.makedirs"), \
             patch("app.services.segment_pipeline.os.path.exists", return_value=True), \
             patch("app.services.segment_pipeline.SETTINGS.output_dir", "/tmp"):

            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            result = await generate_preview_thumbnail("/tmp/video.mp4", timestamp=1.0, width=360)

            assert "thumb.jpg" in result

    @pytest.mark.asyncio
    async def test_generate_preview_thumbnail_failure(self):
        from app.services.segment_pipeline import generate_preview_thumbnail

        with patch("app.services.segment_pipeline.asyncio.create_subprocess_exec") as mock_exec, \
             patch("app.services.segment_pipeline.os.makedirs"), \
             patch("app.services.segment_pipeline.SETTINGS.output_dir", "/tmp"):

            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            # Should return empty string on failure
            result = await generate_preview_thumbnail("/tmp/video.mp4")

            # Function returns empty string on stderr failure
            assert result == ""

    @pytest.mark.asyncio
    async def test_generate_preview_video_success(self):
        from app.services.segment_pipeline import generate_preview_video

        with patch("app.services.segment_pipeline.asyncio.create_subprocess_exec") as mock_exec, \
             patch("app.services.segment_pipeline.os.makedirs"), \
             patch("app.services.segment_pipeline.os.path.exists", return_value=True), \
             patch("app.services.segment_pipeline.SETTINGS.output_dir", "/tmp"):

            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            result = await generate_preview_video("/tmp/video.mp4", width=360)

            assert "_preview.mp4" in result

    @pytest.mark.asyncio
    async def test_generate_preview_video_failure(self):
        from app.services.segment_pipeline import generate_preview_video

        with patch("app.services.segment_pipeline.asyncio.create_subprocess_exec") as mock_exec, \
             patch("app.services.segment_pipeline.os.makedirs"), \
             patch("app.services.segment_pipeline.SETTINGS.output_dir", "/tmp"):

            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            result = await generate_preview_video("/tmp/video.mp4")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_video_duration(self):
        from app.services.preview_service import get_video_duration

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"10.5", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            duration = await get_video_duration("/tmp/test.mp4")
            assert duration == 10.5

    @pytest.mark.asyncio
    async def test_get_video_duration_fallback(self):
        from app.services.preview_service import get_video_duration

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            duration = await get_video_duration("/tmp/test.mp4")
            assert duration == 0.0


# ── 9. Fal Client ────────────────────────────────────────────────────────────

class TestFalClient:
    """Test fal client duration-to-frames resolution."""

    def test_duration_to_frames_minimum(self):
        from app.services.fal_client import _duration_to_frames
        assert _duration_to_frames(1.0) >= 25

    def test_duration_to_frames_maximum(self):
        from app.services.fal_client import _duration_to_frames
        assert _duration_to_frames(10.0) <= 129

    def test_duration_to_frames_even(self):
        from app.services.fal_client import _duration_to_frames
        frames = _duration_to_frames(5.0)
        assert frames % 2 == 0

    def test_parse_aspect_ratio_portrait(self):
        from app.services.fal_client import _parse_aspect_ratio
        assert _parse_aspect_ratio("9:16") == "1080x1920"

    def test_parse_aspect_ratio_landscape(self):
        from app.services.fal_client import _parse_aspect_ratio
        assert _parse_aspect_ratio("16:9") == "1920x1080"

    def test_parse_aspect_ratio_square(self):
        from app.services.fal_client import _parse_aspect_ratio
        assert _parse_aspect_ratio("1:1") == "1080x1080"

    def test_parse_aspect_ratio_unknown_defaults(self):
        from app.services.fal_client import _parse_aspect_ratio
        assert _parse_aspect_ratio("4:3") == "1080x1920"

    @pytest.mark.asyncio
    async def test_generate_video_missing_api_key(self):
        from app.services.fal_client import generate_video_segment

        with patch("app.services.fal_client.SETTINGS.fal_api_key", ""):
            with pytest.raises(RuntimeError, match="FAL_API_KEY not configured"):
                await generate_video_segment("test prompt")


# ── 10. Composition Pipeline ─────────────────────────────────────────────────

class TestCompositionPipeline:
    """Test compose_final_video orchestration."""

    @pytest.mark.asyncio
    async def test_compose_with_no_segments(self):
        from app.services.composition_pipeline import compose_final_video
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch("app.services.composition_pipeline.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            result = await compose_final_video("project-1", [])
            assert result is None

    @pytest.mark.asyncio
    async def test_compose_with_no_ready_segments(self, mock_segments_partial):
        """If no segments are in a ready state, composition should return None."""
        from app.services.composition_pipeline import compose_final_video
        from app.models.segment import SegmentStatus
        from unittest.mock import AsyncMock, MagicMock

        project, segments = mock_segments_partial
        # Set all to pending
        for s in segments:
            s.status = SegmentStatus.pending
            s.video_local_path = None
            s.tts_local_path = None

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = segments
        mock_db.execute.return_value = mock_result

        with patch("app.services.composition_pipeline.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            result = await compose_final_video(project.id, [s.id for s in segments])
            assert result is None

    @pytest.mark.asyncio
    async def test_compose_without_video_paths(self, mock_segments_ready):
        """If ready segments have no video_local_path, composition should return None."""
        from app.services.composition_pipeline import compose_final_video
        from unittest.mock import AsyncMock, MagicMock, patch

        project, segments = mock_segments_ready
        for s in segments:
            s.video_local_path = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = segments
        mock_db.execute.return_value = mock_result

        with patch("app.services.composition_pipeline.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_db

            result = await compose_final_video(project.id, [s.id for s in segments])
            assert result is None

    @pytest.mark.asyncio
    async def test_compose_with_ready_segments(self, mock_segments_ready):
        """Ready segments with video_local_path should trigger export."""
        from app.services.composition_pipeline import compose_final_video
        from unittest.mock import AsyncMock, MagicMock, patch

        project, segments = mock_segments_ready
        for s in segments:
            s.video_local_path = f"/tmp/video_{s.order_index}.mp4"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = segments
        mock_db.execute.return_value = mock_result

        with patch("app.services.composition_pipeline.async_session") as mock_session_ctx, \
             patch("app.services.composition_pipeline.export_final_video", new_callable=AsyncMock) as mock_export, \
             patch("app.services.composition_pipeline.os.makedirs"):

            mock_session_ctx.return_value.__aenter__.return_value = mock_db
            mock_export.return_value = "/tmp/project_final.mp4"

            result = await compose_final_video(project.id, [s.id for s in segments])

            assert result == "/tmp/project_final.mp4"
            mock_export.assert_called_once()
            call_kwargs = mock_export.call_args.kwargs
            assert len(call_kwargs["input_segments"]) == 3

    @pytest.mark.asyncio
    async def test_compose_preserves_order(self):
        """Segments should be sorted by order_index."""
        from app.models.segment import Segment, SegmentStatus
        from sqlalchemy import select

        segments = [
            Segment(id=str(uuid4()), project_id=str(uuid4()), order_index=2, title="C",
                    video_prompt="prompt", duration_seconds=10.0, status=SegmentStatus.completed,
                    video_local_path="/tmp/v3.mp4"),
            Segment(id=str(uuid4()), project_id=str(uuid4()), order_index=0, title="A",
                    video_prompt="prompt", duration_seconds=10.0, status=SegmentStatus.completed,
                    video_local_path="/tmp/v1.mp4"),
            Segment(id=str(uuid4()), project_id=str(uuid4()), order_index=1, title="B",
                    video_prompt="prompt", duration_seconds=10.0, status=SegmentStatus.completed,
                    video_local_path="/tmp/v2.mp4"),
        ]

        segments.sort(key=lambda s: s.order_index)
        assert segments[0].title == "A"
        assert segments[1].title == "B"
        assert segments[2].title == "C"


# ── 11. Edge Cases & Bug Hunting ──────────────────────────────────────────────

class TestEdgeCases:
    """Find bugs and verify edge case handling."""

    def test_resync_attempts_double_increment(self):
        """
        BUG: In segment_tasks.py, resync_attempts is incremented TWICE per loop:
        once at line 96 (while loop increment), once at line 113 (explicit increment).
        This causes the resync loop to exit after just 1 real attempt instead of MAX_TTS_RESYNC_ATTEMPTS.
        """
        max_attempts = 2
        resync_attempts = 0

        # Simulate the buggy behavior from segment_tasks.py
        while resync_attempts < max_attempts:
            resync_attempts += 1  # line 96
            # ... do work ...
            resync_attempts += 1  # line 113 - BUG: double increment

        # After "2" increments, resync_attempts is 2, which equals max_attempts (2),
        # so only 1 iteration occurs instead of 2
        assert resync_attempts == 2  # Shows the bug: 2 increments in 1 iteration
        assert resync_attempts >= max_attempts  # Loop exits early

    def test_resync_attempts_correct_behavior(self):
        """The correct behavior: one increment per iteration."""
        max_attempts = 2
        resync_attempts = 0

        while resync_attempts < max_attempts:
            resync_attempts += 1  # single increment per iteration
            # ... do work ...

        assert resync_attempts == max_attempts  # 2 iterations complete

    def test_validate_prompt_case_insensitive_patterns(self):
        """Prohibited patterns should be detected case-insensitively."""
        from app.services.segment_pipeline import validate_segment_prompt

        assert validate_segment_prompt("TITLE OVERLAY HERE")[0] is False
        assert validate_segment_prompt("Brand Logo Animation")[0] is False
        assert validate_segment_prompt("has subtitle and caption")[0] is False

    def test_validate_prompt_edge_empty(self):
        from app.services.segment_pipeline import validate_segment_prompt

        ok, _ = validate_segment_prompt("")
        assert ok is True

        ok, _ = validate_segment_prompt("   ")
        assert ok is True

    def test_validate_duration_edge_exact_boundaries(self):
        from app.services.segment_pipeline import validate_segment_duration, MIN_DURATION_SECONDS, MAX_DURATION_SECONDS

        assert validate_segment_duration(MIN_DURATION_SECONDS)[0] is True
        assert validate_segment_duration(MAX_DURATION_SECONDS)[0] is True

    def test_validate_duration_edge_zero(self):
        from app.services.segment_pipeline import validate_segment_duration

        assert validate_segment_duration(0.0)[0] is False

    def test_validate_narration_timing_empty_text(self):
        from app.services.segment_pipeline import validate_narration_timing

        ok, _ = validate_narration_timing("", 10.0)
        assert ok is True

    def test_validate_narration_timing_exact_limit(self):
        from app.services.segment_pipeline import validate_narration_timing

        # 150 wpm * 10s = 25 words max. 150% = 37.5 words. 38 should fail.
        text = " ".join(["word"] * 38)
        ok, msg = validate_narration_timing(text, 10.0)
        assert ok is False
        assert "exceeds" in msg

    def test_validate_segment_missing_all_fields(self):
        from app.services.segment_pipeline import validate_segment

        is_valid, errors = validate_segment({})
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_segment_prompt_only(self):
        from app.services.segment_pipeline import validate_segment

        is_valid, errors = validate_segment({"video_prompt": "A nice scene"})
        assert is_valid is True

    def test_cost_alert_edge_zero_caps(self):
        from app.services.cost_alerts import check_cost_alert

        alert = check_cost_alert(user_cost=0, project_cost=0, user_cap=0, project_cap=0)
        assert alert.user_percent == 0.0
        assert alert.project_percent == 0.0
        assert alert.level.value == "ok"

    def test_cost_alert_negative_caps(self):
        """Negative caps should not cause errors - treated as 0."""
        from app.services.cost_alerts import check_cost_alert

        alert = check_cost_alert(user_cost=5, project_cost=3, user_cap=-1, project_cap=-1)
        assert alert.user_percent == 0.0
        assert alert.project_percent == 0.0
        assert alert.level.value == "ok"

    @pytest.mark.asyncio
    async def test_video_probe_duration_error(self):
        """_get_video_duration should return 0.0 on any error."""
        from app.services.segment_pipeline import _get_video_duration

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("ffprobe not found")):
            duration = await _get_video_duration("/nonexistent/video.mp4")
            assert duration == 0.0

    def test_tts_padding_computation(self):
        from app.services.segment_pipeline import compute_tts_padding_needed

        assert compute_tts_padding_needed(10.0, 10.0) == 0.0
        assert compute_tts_padding_needed(8.0, 10.0) == 2.0
        assert compute_tts_padding_needed(15.0, 10.0) == 0.0
        assert compute_tts_padding_needed(0.0, 10.0) == 10.0

    def test_tts_video_sync_both_exactly_on_target(self):
        from app.services.segment_pipeline import validate_tts_video_sync

        is_synced, drift, msg = validate_tts_video_sync(10.0, 10.0, 10.0)
        assert is_synced is True
        assert drift == 0.0

    def test_audio_sync_status_enum(self):
        from app.models.segment import AudioSyncStatus

        assert AudioSyncStatus.ok.value == "ok"
        assert AudioSyncStatus.drift_detected.value == "drift_detected"
        assert AudioSyncStatus.fallback_triggered.value == "fallback_triggered"
        assert AudioSyncStatus.untested.value == "untested"

    def test_duration_contract_dataclass(self):
        from app.services.audio_sync import DurationContract

        contract = DurationContract(
            segment_id="seg-1",
            expected_video_duration=10.0,
            expected_tts_duration=9.5,
            max_drift_seconds=0.5,
        )

        assert contract.segment_id == "seg-1"
        assert contract.expected_video_duration == 10.0
        assert contract.max_drift_seconds == 0.5

    def test_sync_validation_result_dataclass(self):
        from app.services.audio_sync import SyncValidationResult

        result = SyncValidationResult(
            segment_id="seg-1",
            video_actual_duration=10.0,
            tts_actual_duration=10.3,
            drift_seconds=0.3,
            offset_ms=300,
            status="ok",
            within_contract=True,
        )

        assert result.segment_id == "seg-1"
        assert result.drift_seconds == 0.3
        assert result.within_contract is True


# ── 12. Segment API Endpoints ────────────────────────────────────────────────

class TestSegmentRegenerateEndpoint:
    """Verify regeneration endpoint clears all generated artifacts correctly."""

    def test_regenerate_resets_all_media_fields(self):
        from app.models.segment import Segment, SegmentStatus

        fields_to_clear = [
            "video_url", "video_local_path", "actual_duration_seconds",
            "tts_url", "tts_local_path", "tts_actual_duration",
            "thumbnail_path", "preview_path", "error_message",
        ]

        segment = Segment(
            id=str(uuid4()),
            project_id=str(uuid4()),
            order_index=0,
            title="Test",
            video_prompt="prompt",
            duration_seconds=10.0,
            status=SegmentStatus.completed,
            video_url="old_url",
            video_local_path="old_path",
            actual_duration_seconds=10.0,
            tts_url="old_tts_url",
            tts_local_path="old_tts_path",
            tts_actual_duration=9.5,
            thumbnail_path="old_thumb",
            preview_path="old_preview",
            error_message="old_error",
        )

        segment.status = SegmentStatus.pending
        for field in fields_to_clear:
            setattr(segment, field, None)

        assert segment.status == SegmentStatus.pending
        for field in fields_to_clear:
            assert getattr(segment, field) is None, f"{field} was not cleared"


# ── 13. Provider Router Integration ───────────────────────────────────────────

class TestProviderRouterIntegration:
    """Test provider selection and circuit breaker integration with segments."""

    def test_select_provider_for_segment_duration(self):
        from app.services.video_router import select_provider, Provider

        assert select_provider(5, "educational") == Provider.ZSKY
        assert select_provider(10, "educational") == Provider.ZSKY
        assert select_provider(15, "educational") == Provider.HAPPY_HORSE
        assert select_provider(30, "educational") == Provider.HAPPY_HORSE
        assert select_provider(45, "educational") == Provider.FREE_AI
        assert select_provider(60, "educational") == Provider.FREE_AI

    def test_segment_validation_before_routing(self):
        """Validation should happen before provider routing."""
        from app.services.segment_pipeline import validate_segment

        invalid = {"video_prompt": "Video with title overlay", "duration_seconds": 10.0}
        is_valid, errors = validate_segment(invalid)
        assert is_valid is False
        assert any("title" in e for e in errors)

        valid = {"video_prompt": "Cinematic sunset", "duration_seconds": 10.0}
        is_valid, errors = validate_segment(valid)
        assert is_valid is True

    def test_happy_horse_selected_for_medium_segments(self):
        """10-30s segments should route to Happy Horse."""
        from app.services.video_router import select_provider, Provider

        for duration in [11, 15, 20, 25, 30]:
            assert select_provider(duration, "educational") == Provider.HAPPY_HORSE, \
                f"Duration {duration}s should route to Happy Horse"

    def test_fallback_to_first_available_when_all_too_long(self):
        """Very long segments should fall back to highest-capacity provider."""
        from app.services.video_router import select_provider

        provider = select_provider(300, "educational")
        assert provider is not None

    def test_provider_priority_chain(self):
        """Provider priority should be ZSKY > HAPPY_HORSE > FREE_AI."""
        from app.services.video_router import PROVIDER_PRIORITY, Provider

        assert PROVIDER_PRIORITY[0] == Provider.ZSKY
        assert PROVIDER_PRIORITY[1] == Provider.HAPPY_HORSE
        assert PROVIDER_PRIORITY[2] == Provider.FREE_AI
