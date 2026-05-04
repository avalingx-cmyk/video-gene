import pytest
import uuid
from unittest.mock import AsyncMock
from datetime import datetime, timedelta


class TestAuditLogs:

    @pytest.mark.asyncio
    async def test_list_audit_logs(self, mock_db, mock_current_user, sample_audit_log):
        from app.api.v1.endpoints.audit import list_audit_logs

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_audit_log]
        mock_db.execute.return_value = mock_result

        result = await list_audit_logs(
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 1
        assert result[0].action == "project.created"
        assert result[0].entity_type == "project"

    @pytest.mark.asyncio
    async def test_list_audit_logs_filter_by_action(self, mock_db, mock_current_user, sample_audit_log):
        from app.api.v1.endpoints.audit import list_audit_logs

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_audit_log]
        mock_db.execute.return_value = mock_result

        result = await list_audit_logs(
            action="project.created",
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_audit_logs_filter_by_date_range(self, mock_db, mock_current_user, sample_audit_log):
        from app.api.v1.endpoints.audit import list_audit_logs

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_audit_log]
        mock_db.execute.return_value = mock_result

        since = datetime.utcnow() - timedelta(days=7)
        until = datetime.utcnow()

        result = await list_audit_logs(
            since=since,
            until=until,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_audit_log(self, mock_db, mock_current_user, sample_audit_log):
        from app.api.v1.endpoints.audit import get_audit_log

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_audit_log
        mock_db.execute.return_value = mock_result

        result = await get_audit_log(
            log_id=str(sample_audit_log.id),
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.action == "project.created"

    @pytest.mark.asyncio
    async def test_get_audit_log_not_found(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.audit import get_audit_log
        from fastapi import HTTPException

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_audit_log(
                log_id=str(uuid.uuid4()),
                db=mock_db,
                current_user=mock_current_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_audit_log_summary(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.audit import audit_log_summary

        mock_result = AsyncMock()
        mock_result.all.return_value = [("project.created", 5), ("project.published", 3)]
        mock_db.execute.return_value = mock_result

        result = await audit_log_summary(
            days=30,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 2
        assert result[0]["action"] == "project.created"
        assert result[0]["count"] == 5

    @pytest.mark.asyncio
    async def test_record_audit_log(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.audit import record_audit_log

        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        result = await record_audit_log(
            db=mock_db,
            user_id=str(mock_current_user.id),
            action="test.action",
            entity_type="test",
            entity_id=str(uuid.uuid4()),
            details={"key": "value"},
        )

        assert result.action == "test.action"
        assert result.details == {"key": "value"}
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, mock_db, mock_current_user, sample_audit_log):
        from app.api.v1.endpoints.audit import export_audit_logs_csv

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_audit_log]
        mock_db.execute.return_value = mock_result

        response = await export_audit_logs_csv(
            db=mock_db,
            current_user=mock_current_user,
        )

        assert response.media_type == "text/csv"
        assert "audit_log_" in response.headers.get("content-disposition", "")
