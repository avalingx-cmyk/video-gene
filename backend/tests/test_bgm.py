import pytest
import uuid
from unittest.mock import AsyncMock

from sqlalchemy import select


class TestBgmTracks:

    @pytest.mark.asyncio
    async def test_create_bgm_track(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.bgm import create_bgm_track
        from app.schemas.assets import BgmTrackCreate

        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        track_data = BgmTrackCreate(
            title="Test Track",
            artist="Test Artist",
            genre="ambient",
            duration_seconds=180.0,
            url="https://example.com/track.mp3",
        )

        result = await create_bgm_track(
            data=track_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.title == "Test Track"
        assert result.artist == "Test Artist"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_bgm_tracks(self, mock_db, mock_current_user, sample_bgm_track):
        from app.api.v1.endpoints.bgm import list_bgm_tracks

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_bgm_track]
        mock_db.execute.return_value = mock_result

        result = await list_bgm_tracks(
            db=mock_db,
        )

        assert len(result) == 1
        assert result[0].title == "Test Track"
        assert result[0].genre == "ambient"

    @pytest.mark.asyncio
    async def test_list_bgm_tracks_filter_by_genre(self, mock_db, mock_current_user, sample_bgm_track):
        from app.api.v1.endpoints.bgm import list_bgm_tracks

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_bgm_track]
        mock_db.execute.return_value = mock_result

        result = await list_bgm_tracks(
            genre="ambient",
            db=mock_db,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_bgm_tracks_filter_by_search(self, mock_db, mock_current_user, sample_bgm_track):
        from app.api.v1.endpoints.bgm import list_bgm_tracks

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_bgm_track]
        mock_db.execute.return_value = mock_result

        result = await list_bgm_tracks(
            search="Test",
            db=mock_db,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_bgm_track_not_found(self, mock_db):
        from app.api.v1.endpoints.bgm import get_bgm_track
        from fastapi import HTTPException

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_bgm_track(
                track_id=str(uuid.uuid4()),
                db=mock_db,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_bgm_track(self, mock_db, mock_current_user, sample_bgm_track):
        from app.api.v1.endpoints.bgm import delete_bgm_track

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_bgm_track
        mock_db.execute.return_value = mock_result
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        result = await delete_bgm_track(
            track_id=str(sample_bgm_track.id),
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result is None
        mock_db.delete.assert_called_once_with(sample_bgm_track)

    @pytest.mark.asyncio
    async def test_list_genres(self, mock_db):
        from app.api.v1.endpoints.bgm import list_bgm_genres

        mock_result = AsyncMock()
        mock_result.all.return_value = [("ambient",), ("jazz",)]
        mock_db.execute.return_value = mock_result

        result = await list_bgm_genres(db=mock_db)

        assert result == ["ambient", "jazz"]
