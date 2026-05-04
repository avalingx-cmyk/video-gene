from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AssetLicenseCreate(BaseModel):
    asset_type: str
    asset_url: str
    asset_name: str
    content_hash: Optional[str] = None
    license_type: str
    license_url: Optional[str] = None
    attribution_required: bool = False
    attribution_text: Optional[str] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class AssetLicenseUpdate(BaseModel):
    asset_type: Optional[str] = None
    asset_url: Optional[str] = None
    asset_name: Optional[str] = None
    content_hash: Optional[str] = None
    license_type: Optional[str] = None
    license_url: Optional[str] = None
    attribution_required: Optional[bool] = None
    attribution_text: Optional[str] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class AssetLicenseResponse(BaseModel):
    id: str
    user_id: str
    asset_type: str
    asset_url: str
    asset_name: str
    content_hash: Optional[str] = None
    license_type: str
    license_url: Optional[str] = None
    attribution_required: bool
    attribution_text: Optional[str] = None
    expires_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BgmTrackCreate(BaseModel):
    title: str
    artist: str
    genre: str = "ambient"
    duration_seconds: float
    url: str
    file_path: Optional[str] = None
    mood_tags: Optional[str] = None
    bpm: Optional[int] = None
    is_royalty_free: bool = True
    license_type: str = "royalty_free"
    attribution_required: bool = False
    attribution_text: Optional[str] = None


class BgmTrackUpdate(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    genre: Optional[str] = None
    duration_seconds: Optional[float] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    mood_tags: Optional[str] = None
    bpm: Optional[int] = None
    is_royalty_free: Optional[bool] = None
    license_type: Optional[str] = None
    attribution_required: Optional[bool] = None
    attribution_text: Optional[str] = None
    is_active: Optional[bool] = None


class BgmTrackResponse(BaseModel):
    id: str
    title: str
    artist: str
    genre: str
    duration_seconds: float
    url: str
    file_path: Optional[str] = None
    mood_tags: Optional[str] = None
    bpm: Optional[int] = None
    is_royalty_free: bool
    license_type: str
    attribution_required: bool
    attribution_text: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
