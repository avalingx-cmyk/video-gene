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

    s3_endpoint_url: str = ""
    s3_bucket: str = "videogene"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    rate_limit_requests_per_minute: int = 10

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
