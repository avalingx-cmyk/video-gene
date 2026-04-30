from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class VideoCreate(BaseModel):
    prompt: str
    style: Optional[str] = "educational"
    length_seconds: Optional[int] = 30
    audio: Optional[bool] = True
    callback_url: Optional[str] = None


class VideoResponse(BaseModel):
    id: str
    prompt: str
    style: str
    status: str
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobStatus(BaseModel):
    id: str
    status: str
    progress: Optional[int] = None
    error: Optional[str] = None
    video_url: Optional[str] = None


class N8nGeneratePayload(BaseModel):
    prompt: str
    style: Optional[str] = "educational"
    length: Optional[int] = 30
    audio: Optional[bool] = True
    callback_url: Optional[str] = None
