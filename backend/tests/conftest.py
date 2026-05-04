import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_current_user():
    from app.models.video import User
    return User(
        id=uuid.uuid4(),
        email="test@decepticon.com",
        hashed_password="hashed_megatron_approves",
        api_key=None,
        cost_cap=10.0,
        total_cost=0.0,
        can_upload=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_asset_license(mock_current_user):
    from app.models.assets import AssetLicense
    return AssetLicense(
        id=uuid.uuid4(),
        user_id=mock_current_user.id,
        asset_type="video",
        asset_url="https://example.com/video.mp4",
        asset_name="Test Video",
        content_hash=None,
        license_type="royalty_free",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution_required=True,
        attribution_text="CC BY 4.0 — Test Creator",
        expires_at=None,
        verified_at=None,
        verified_by=None,
        notes=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_bgm_track():
    from app.models.assets import BgmTrack
    return BgmTrack(
        id=uuid.uuid4(),
        title="Test Track",
        artist="Test Artist",
        genre="ambient",
        duration_seconds=180.0,
        url="https://example.com/track.mp3",
        file_path=None,
        mood_tags="calm,peaceful",
        bpm=70,
        is_royalty_free=True,
        license_type="royalty_free",
        attribution_required=False,
        attribution_text=None,
        is_active=True,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_audit_log(mock_current_user):
    from app.models.assets import AuditLog
    return AuditLog(
        id=uuid.uuid4(),
        user_id=mock_current_user.id,
        action="project.created",
        entity_type="project",
        entity_id=str(uuid.uuid4()),
        details={"title": "Test Project"},
        ip_address="192.168.1.1",
        user_agent="pytest/1.0",
        created_at=datetime.utcnow(),
    )
