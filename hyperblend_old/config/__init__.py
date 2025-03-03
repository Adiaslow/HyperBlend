"""Configuration module for HyperBlend."""

from typing import Dict, Any
from pydantic import BaseModel
from functools import lru_cache


class Settings(BaseModel):
    """Application settings."""

    PROJECT_NAME: str = "HyperBlend"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "A chemical compound analysis and visualization platform"
    DATABASE_URL: str = "sqlite+aiosqlite:///hyperblend.db"
    DATABASE_ARGS: Dict[str, Any] = {
        "echo": False,
        "future": True,
    }
    BACKEND_CORS_ORIGINS: list[str] = ["*"]


settings = Settings()


@lru_cache()
def get_settings() -> Settings:
    """Get application settings."""
    return settings


__all__ = ["Settings", "settings", "get_settings"]
