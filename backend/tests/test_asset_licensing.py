import hashlib
import pytest


class TestAssetLicensing:

    def test_compute_sha256(self):
        from app.services.asset_licensing import compute_sha256
        result = compute_sha256(b"hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert result == expected

    def test_compute_sha256_empty(self):
        from app.services.asset_licensing import compute_sha256
        result = compute_sha256(b"")
        assert result == hashlib.sha256(b"").hexdigest()

    def test_compute_sha256_from_url(self):
        from app.services.asset_licensing import compute_sha256_from_url
        url = "https://example.com/video.mp4"
        result = compute_sha256_from_url(url)
        assert len(result) == 64
        assert isinstance(result, str)
        assert result == hashlib.sha256(url.encode("utf-8")).hexdigest()

    def test_content_hash_uniqueness(self):
        from app.services.asset_licensing import compute_sha256_from_url
        url1 = "https://example.com/video1.mp4"
        url2 = "https://example.com/video2.mp4"
        assert compute_sha256_from_url(url1) != compute_sha256_from_url(url2)

    def test_check_upload_rights_allowed(self, mock_current_user):
        from app.services.asset_licensing import check_upload_rights
        mock_current_user.can_upload = True
        result = check_upload_rights(current_user=mock_current_user)
        assert result == mock_current_user

    @pytest.mark.asyncio
    async def test_check_upload_rights_revoked(self, mock_current_user):
        from app.services.asset_licensing import check_upload_rights
        from fastapi import HTTPException
        mock_current_user.can_upload = False
        with pytest.raises(HTTPException) as exc:
            await check_upload_rights(current_user=mock_current_user)
        assert exc.value.status_code == 403
        assert "Upload rights revoked" in exc.value.detail

    @pytest.mark.asyncio
    async def test_find_asset_by_hash_found(self, mock_db, sample_asset_license):
        from app.services.asset_licensing import find_asset_by_hash
        from unittest.mock import AsyncMock

        sample_asset_license.content_hash = "abc123"
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_asset_license
        mock_db.execute.return_value = mock_result

        result = await find_asset_by_hash("abc123", mock_db)
        assert result is not None
        assert result.content_hash == "abc123"

    @pytest.mark.asyncio
    async def test_find_asset_by_hash_not_found(self, mock_db):
        from app.services.asset_licensing import find_asset_by_hash
        from unittest.mock import AsyncMock

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await find_asset_by_hash("nonexistent", mock_db)
        assert result is None
