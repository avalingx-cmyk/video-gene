from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    project_name: str = "Video Generator"
    project_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/videogene"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    replicate_api_token: str = ""
    elevenlabs_api_key: str = ""
    youtube_api_key: str = ""
    youtube_client_secret: str = ""

    fal_api_key: str = ""
    groq_api_key: str = ""
    suno_api_key: str = ""
    openai_api_key: str = ""

    output_dir: str = "/tmp/videogene/output"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    s3_endpoint_url: str = ""
    s3_bucket: str = "videogene"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    rate_limit_requests_per_minute: int = 10

    fal_cost_per_second: float = 0.0
    groq_cost_per_token: float = 0.0
    suno_cost_perGeneration: float = 0.0

    default_cost_cap_per_user: float = 10.0
    default_cost_cap_per_project: float = 5.0

    cost_alert_threshold: float = 0.8
    cost_hard_stop_threshold: float = 1.0

    batch_size: int = 5

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
