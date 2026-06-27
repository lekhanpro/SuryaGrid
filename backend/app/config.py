"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Suryagrid AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database — defaults to local SQLite (no server needed); set DATABASE_URL
    # to a postgresql+asyncpg URL for production / TimescaleDB.
    DATABASE_URL: str = "sqlite+aiosqlite:///./suryagrid.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Real-time ingestion scheduler (off by default; opt-in for live polling)
    SCHEDULER_ENABLED: bool = False
    INGEST_INTERVAL_MINUTES: int = 15

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
