from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TextOverlayCreate(BaseModel):
    text: str
    font_family: str = "Arial"
    font_size: int = 48
    font_color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 2
    position_x: float = 0.5
    position_y: float = 0.5
    anchor: str = "center"
    start_time: float = 0.0
    end_time: float = 10.0
    animation: str = "none"


class TextOverlayUpdate(BaseModel):
    text: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    font_color: Optional[str] = None
    stroke_color: Optional[str] = None
    stroke_width: Optional[int] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    anchor: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    animation: Optional[str] = None


class TextOverlayResponse(BaseModel):
    id: str
    segment_id: str
    text: str
    font_family: str
    font_size: int
    font_color: str
    stroke_color: str
    stroke_width: int
    position_x: float
    position_y: float
    anchor: str
    start_time: float
    end_time: float
    animation: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SegmentCreate(BaseModel):
    title: str
    narration_text: Optional[str] = None
    video_prompt: str
    duration_seconds: float = 10.0
    transition: str = "fade"


class SegmentUpdate(BaseModel):
    title: Optional[str] = None
    narration_text: Optional[str] = None
    video_prompt: Optional[str] = None
    duration_seconds: Optional[float] = None
    transition: Optional[str] = None
    order_index: Optional[int] = None
    video_local_path: Optional[str] = None
    actual_duration_seconds: Optional[float] = None
    tts_local_path: Optional[str] = None
    tts_actual_duration: Optional[float] = None
    thumbnail_path: Optional[str] = None
    preview_path: Optional[str] = None
    error_message: Optional[str] = None


class SegmentResponse(BaseModel):
    id: str
    project_id: str
    order_index: int
    title: str
    narration_text: Optional[str]
    video_prompt: str
    duration_seconds: float
    transition: str
    status: str
    video_url: Optional[str] = None
    video_local_path: Optional[str] = None
    actual_duration_seconds: Optional[float] = None
    tts_url: Optional[str] = None
    tts_local_path: Optional[str] = None
    tts_actual_duration: Optional[float] = None
    error_message: Optional[str] = None
    thumbnail_path: Optional[str] = None
    preview_path: Optional[str] = None
    text_overlays: list[TextOverlayResponse] = []
    is_deleted: bool = False
    cost: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedSegmentsResponse(BaseModel):
    segments: list[SegmentResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


class ProjectCreate(BaseModel):
    title: str
    prompt: str
    style: str = "educational"
    resolution_width: int = 1080
    resolution_height: int = 1920


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    style: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    prompt: str
    style: str
    resolution_width: int
    resolution_height: int
    status: str
    output_url: Optional[str] = None
    error_message: Optional[str] = None
    segments: list[SegmentResponse] = []
    published_at: Optional[datetime] = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateScriptRequest(BaseModel):
    prompt: str
    style: str = "educational"
    num_segments: int = 3
    segment_duration: float = 10.0


class SegmentScript(BaseModel):
    title: str
    narration_text: str
    video_prompt: str
    duration_seconds: float
    transition: str = "fade"


class GenerateScriptResponse(BaseModel):
    segments: list[SegmentScript]


class GenerateTTSRequest(BaseModel):
    text: str
    voice: str = "alto"


class GenerateVideoRequest(BaseModel):
    prompt: str
    duration_seconds: float = 10.0
    aspect_ratio: str = "9:16"


class ExportProjectRequest(BaseModel):
    background_music_url: Optional[str] = None
    fade_in_duration: float = 0.0
    fade_out_duration: float = 0.5
    enable_sidechain_ducking: bool = True
    transition_duration: float = 1.0


class SegmentReorder(BaseModel):
    segment_ids: list[str]