"""Application settings, loaded from environment (.env)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    # PostgreSQL is the production database (see manual §3). SQLite is allowed
    # so teammates can run the API without a local Postgres instance.
    database_url: str = "postgresql+psycopg://portal:portal@localhost:5432/portal"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    upload_dir: Path = BASE_DIR / "uploads"
    max_resume_bytes: int = 5 * 1024 * 1024

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resume_dir(self) -> Path:
        return self.upload_dir / "resumes"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.resume_dir.mkdir(parents=True, exist_ok=True)
    return settings
