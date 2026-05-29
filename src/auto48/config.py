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


@lru_cache
def get_settings() -> Settings:
    return Settings()
