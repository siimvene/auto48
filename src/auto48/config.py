"""Application settings sourced from environment variables.

Per component-technical-standards: env-based config only, no external config files,
no module-level singleton. Use the `get_settings()` factory (cached) everywhere.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTO48_", env_file=".env", extra="ignore")

    app_name: str = "auto48"
    environment: str = "local"
    debug: bool = False

    # Browser origins allowed to call the API (the Nuxt frontend runs on a
    # different origin in dev). Override via AUTO48_CORS_ORIGINS as a
    # comma-separated list in real environments. Never use "*" with credentials.
    # NoDecode: stop pydantic-settings from JSON-decoding the env value so the
    # comma-split validator below can parse a plain CSV string (e.g.
    # "https://kekec.ee,https://www.kekec.ee") without a SettingsError.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv_origins(cls, v: object) -> object:
        """Accept a comma-separated string from the environment."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

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

    # Stripe (Phase 1b: dealer subscriptions + promotions). Empty → StubPaymentAdapter.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # SMTP for saved-search alert emails (Phase 1b). Empty host → StubNotifyAdapter.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "auto48 <noreply@auto48.ee>"


@lru_cache
def get_settings() -> Settings:
    return Settings()
