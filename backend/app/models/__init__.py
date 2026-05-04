from app.models.video import Base, User, Video, VideoStatus
from app.models.segment import VideoProject, ProjectStatus, Segment, SegmentStatus, TextOverlay
from app.models.assets import AssetLicense, AssetType, LicenseType, BgmTrack, AuditLog
from app.models.draft_state import DraftState, SegmentVersion, SegmentRetention, PublishStatus, _late_bind_relationships

_late_bind_relationships()

__all__ = [
    "Base",
    "User",
    "Video",
    "VideoStatus",
    "VideoProject",
    "ProjectStatus",
    "Segment",
    "SegmentStatus",
    "TextOverlay",
    "AssetLicense",
    "AssetType",
    "LicenseType",
    "BgmTrack",
    "AuditLog",
    "DraftState",
    "SegmentVersion",
    "SegmentRetention",
    "PublishStatus",
]