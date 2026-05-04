import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestCostAlerts:
    def test_cost_alert_ok(self):
        from app.services.cost_alerts import check_cost_alert, CostAlertLevel

        alert = check_cost_alert(
            user_cost=1.0,
            project_cost=1.0,
            user_cap=10.0,
            project_cap=5.0,
            alert_threshold=0.8,
            hard_stop_threshold=1.0,
        )

        assert alert.level == CostAlertLevel.OK
        assert alert.user_percent == 0.1
        assert alert.project_percent == 0.2

    def test_cost_alert_warning(self):
        from app.services.cost_alerts import check_cost_alert, CostAlertLevel

        alert = check_cost_alert(
            user_cost=8.0,
            project_cost=4.0,
            user_cap=10.0,
            project_cap=5.0,
            alert_threshold=0.8,
            hard_stop_threshold=1.0,
        )

        assert alert.level == CostAlertLevel.WARNING
        assert alert.user_percent == 0.8
        assert alert.project_percent == 0.8
        assert alert.can_override is True

    def test_cost_alert_hard_stop(self):
        from app.services.cost_alerts import check_cost_alert, CostAlertLevel

        alert = check_cost_alert(
            user_cost=10.0,
            project_cost=5.0,
            user_cap=10.0,
            project_cap=5.0,
            alert_threshold=0.8,
            hard_stop_threshold=1.0,
        )

        assert alert.level == CostAlertLevel.HARD_STOP
        assert alert.can_override is True

    def test_should_stop_for_cost_no_override(self):
        from app.services.cost_alerts import should_stop_for_cost, CostAlertLevel

        stop, alert = should_stop_for_cost(
            user_cost=10.0,
            project_cost=5.0,
            user_cap=10.0,
            project_cap=5.0,
            override=False,
            alert_threshold=0.8,
            hard_stop_threshold=1.0,
        )

        assert stop is True
        assert alert.level == CostAlertLevel.HARD_STOP

    def test_should_stop_for_cost_with_override(self):
        from app.services.cost_alerts import should_stop_for_cost, CostAlertLevel

        stop, alert = should_stop_for_cost(
            user_cost=10.0,
            project_cost=5.0,
            user_cap=10.0,
            project_cap=5.0,
            override=True,
            alert_threshold=0.8,
            hard_stop_threshold=1.0,
        )

        assert stop is False
        assert alert.level == CostAlertLevel.HARD_STOP


class TestCostInfo:
    def test_can_afford_within_budget(self):
        from app.services.batch_generation import CostInfo

        cost_info = CostInfo(
            user_cost=5.0,
            project_cost=2.0,
            user_cap=10.0,
            project_cap=5.0,
        )

        assert cost_info.can_afford(1.0) is True
        assert cost_info.can_afford(5.0) is False

    def test_remaining_budget(self):
        from app.services.batch_generation import CostInfo

        cost_info = CostInfo(
            user_cost=5.0,
            project_cost=2.0,
            user_cap=10.0,
            project_cap=5.0,
        )

        assert cost_info.remaining_user_budget() == 5.0
        assert cost_info.remaining_project_budget() == 3.0

    def test_remaining_budget_no_cap(self):
        from app.services.batch_generation import CostInfo

        cost_info = CostInfo(
            user_cost=5.0,
            project_cost=2.0,
            user_cap=None,
            project_cap=None,
        )

        assert cost_info.remaining_user_budget() is None
        assert cost_info.remaining_project_budget() is None


class TestSegmentModel:
    def test_segment_status_enum(self):
        from app.models.segment import SegmentStatus

        assert SegmentStatus.pending.value == "pending"
        assert SegmentStatus.video_generating.value == "video_generating"
        assert SegmentStatus.completed.value == "completed"
        assert SegmentStatus.failed.value == "failed"

    def test_project_status_enum(self):
        from app.models.segment import ProjectStatus

        assert ProjectStatus.draft.value == "draft"
        assert ProjectStatus.generating.value == "generating"
        assert ProjectStatus.published.value == "published"


class TestBatchGenerationServiceUnit:
    @pytest.mark.asyncio
    async def test_get_pending_segments_filters_correctly(self):
        from app.services.batch_generation import BatchGenerationService
        from app.models.segment import SegmentStatus
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()
        mock_project_id = "test-project-id"

        service = BatchGenerationService(mock_db, mock_project_id)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        segments = await service.get_pending_segments()

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "pending" in str(call_args)


class TestPreviewService:
    @pytest.mark.asyncio
    async def test_get_video_duration(self):
        from app.services.preview_service import get_video_duration

        with patch("app.services.preview_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"10.5", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            duration = await get_video_duration("/fake/path.mp4")

            assert duration == 10.5

    @pytest.mark.asyncio
    async def test_get_video_duration_fallback(self):
        from app.services.preview_service import get_video_duration

        with patch("app.services.preview_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            duration = await get_video_duration("/fake/path.mp4")

            assert duration == 0.0


class TestSegmentCheckpointResume:
    """Tests for checkpoint resume after worker restart"""

    @pytest.mark.asyncio
    async def test_segment_status_transitions(self):
        from app.models.segment import SegmentStatus

        transitions = [
            (SegmentStatus.pending, SegmentStatus.video_generating),
            (SegmentStatus.video_generating, SegmentStatus.video_ready),
            (SegmentStatus.video_ready, SegmentStatus.tts_generating),
            (SegmentStatus.tts_generating, SegmentStatus.tts_ready),
            (SegmentStatus.tts_ready, SegmentStatus.completed),
        ]

        for from_status, to_status in transitions:
            assert from_status.value != to_status.value

    def test_segment_cost_accumulates(self):
        """Test that segment costs are tracked"""
        from app.models.segment import Segment

        segment = Segment(
            id="test-id",
            project_id="test-project",
            order_index=0,
            title="Test",
            video_prompt="test prompt",
            cost=0.0,
        )

        segment.cost = 0.5
        assert segment.cost == 0.5

        segment.cost += 0.3
        assert segment.cost == 0.8


class TestPaginationSchemas:
    def test_paginated_segments_response(self):
        from app.schemas.segment import PaginatedSegmentsResponse, SegmentResponse

        response = PaginatedSegmentsResponse(
            segments=[],
            total=10,
            offset=0,
            limit=5,
            has_more=True,
        )

        assert response.total == 10
        assert response.offset == 0
        assert response.limit == 5
        assert response.has_more is True

    def test_segment_response_has_cost(self):
        from app.schemas.segment import SegmentResponse
        from datetime import datetime

        segment = SegmentResponse(
            id="test-id",
            project_id="test-project",
            order_index=0,
            title="Test",
            narration_text="Test narration",
            video_prompt="Test prompt",
            duration_seconds=10.0,
            transition="fade",
            status="completed",
            is_deleted=False,
            cost=1.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert segment.cost == 1.5
