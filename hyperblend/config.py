# hyperblend/config.py

"""Configuration settings for the HyperBlend system."""

from typing import Optional, Dict, Any
from pydantic import BaseModel
from functools import lru_cache


class Settings(BaseModel):
    """Application settings."""

    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///hyperblend.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # API settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "HyperBlend"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Advanced botanical medicine analysis using hypergraph networks"

    # Security settings
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",
    ]

    # Graph analysis settings
    MIN_SIMILARITY_THRESHOLD: float = 0.7
    MAX_SIMILAR_RESULTS: int = 10
    CONFIDENCE_THRESHOLD: float = 0.5

    @property
    def DATABASE_ARGS(self) -> Dict[str, Any]:
        """Get database connection arguments."""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "connect_args": {"check_same_thread": False},
        }

    class Config:
        """Pydantic model configuration."""

        env_file = ".env"
        case_sensitive = True
        frozen = True


@lru_cache()
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
