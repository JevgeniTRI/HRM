from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./hrm.db"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]"]
    media_root: Path = Path(__file__).resolve().parents[2] / "media"
    cookie_secure: bool = False
    session_hours: int = Field(default=12, ge=1, le=168)

    model_config = SettingsConfigDict(env_prefix="HRM_", env_file=".env", extra="ignore")

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            url = urlsplit(origin)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.path
                or url.query
                or url.fragment
                or "*" in origin
            ):
                raise ValueError("Укажите точные HTTP/HTTPS Origin без пути и wildcard")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
