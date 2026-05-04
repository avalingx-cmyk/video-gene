import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock

from sqlalchemy import select


class TestAssetLicenses:

    @pytest.mark.asyncio
    async def test_create_asset_license(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.licenses import create_asset_license
        from app.schemas.assets import AssetLicenseCreate

        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        license_data = AssetLicenseCreate(
            asset_type="video",
            asset_url="https://example.com/video.mp4",
            asset_name="Test Video",
            license_type="royalty_free",
        )

        result = await create_asset_license(
            data=license_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.asset_name == "Test Video"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_asset_license_duplicate_hash(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.licenses import create_asset_license
        from app.schemas.assets import AssetLicenseCreate
        from fastapi import HTTPException
        from unittest.mock import AsyncMock

        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        existing_mock = AsyncMock()
        existing_mock.scalar_one_or_none.return_value = True
        mock_db.execute.return_value = existing_mock

        license_data = AssetLicenseCreate(
            asset_type="video",
            asset_url="https://example.com/video.mp4",
            asset_name="Duplicate Video",
            license_type="royalty_free",
        )

        with pytest.raises(HTTPException) as exc:
            await create_asset_license(
                data=license_data,
                db=mock_db,
                current_user=mock_current_user,
            )
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_list_licenses(self, mock_db, mock_current_user, sample_asset_license):
        from app.api.v1.endpoints.licenses import list_asset_licenses

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_asset_license]
        mock_db.execute.return_value = mock_result

        result = await list_asset_licenses(
            db=mock_db,
            current_user=mock_current_user,
        )

        assert len(result) == 1
        assert result[0].asset_name == "Test Video"

    @pytest.mark.asyncio
    async def test_get_license(self, mock_db, mock_current_user, sample_asset_license):
        from app.api.v1.endpoints.licenses import get_asset_license

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_license
        mock_db.execute.return_value = mock_result

        result = await get_asset_license(
            asset_id=str(sample_asset_license.id),
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.asset_name == "Test Video"

    @pytest.mark.asyncio
    async def test_get_license_not_found(self, mock_db, mock_current_user):
        from app.api.v1.endpoints.licenses import get_asset_license
        from fastapi import HTTPException

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_asset_license(
                asset_id=str(uuid.uuid4()),
                db=mock_db,
                current_user=mock_current_user,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_license(self, mock_db, mock_current_user, sample_asset_license):
        from app.api.v1.endpoints.licenses import verify_asset_license

        sample_asset_license.verified_at = None
        sample_asset_license.verified_by = None

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_license
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.return_value = sample_asset_license

        result = await verify_asset_license(
            asset_id=str(sample_asset_license.id),
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.verified_at is not None

    @pytest.mark.asyncio
    async def test_update_license(self, mock_db, mock_current_user, sample_asset_license):
        from app.api.v1.endpoints.licenses import update_asset_license
        from app.schemas.assets import AssetLicenseUpdate

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_license
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.return_value = sample_asset_license

        update_data = AssetLicenseUpdate(asset_name="Updated Name")

        result = await update_asset_license(
            asset_id=str(sample_asset_license.id),
            data=update_data,
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_delete_license(self, mock_db, mock_current_user, sample_asset_license):
        from app.api.v1.endpoints.licenses import delete_asset_license

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_license
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.delete = AsyncMock()

        result = await delete_asset_license(
            asset_id=str(sample_asset_license.id),
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result is None
        mock_db.delete.assert_called_once_with(sample_asset_license)
