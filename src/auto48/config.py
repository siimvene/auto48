"""Application settings sourced from environment variables.

Per component-technical-standards: env-based config only, no external config files,
no module-level singleton. Use the `get_settings()` factory (cached) everywhere.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTO48_", env_file=".env", extra="ignore")

    app_name: str = "auto48"
    environment: str = "local"
    debug: bool = False

    # Async SQLAlchemy URL. Defaults to local sqlite for zero-config dev;
    # set AUTO48_DATABASE_URL to a postgresql+asyncpg://... DSN in real envs.
    database_url: str = "sqlite+aiosqlite:///./auto48.db"

    # JWT configuration — override AUTO48_JWT_SECRET in non-local environments.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_minutes: int = 60

    # Vehicle-data API (carVertical / autoDNA). Leave empty to use StubAdapter.
    vehicle_data_api_url: str = ""
    vehicle_data_api_key: str = ""

    # S3-compatible object storage (MinIO / AWS S3).  All empty → StubMediaAdapter.
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "auto48-media"

    # Redis URL used by arq workers and job enqueueing.
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
