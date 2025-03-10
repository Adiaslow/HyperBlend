#!/usr/bin/env python3
# hyperblend/app/config/settings.py

"""
Configuration settings for the HyperBlend application.
Uses Pydantic for settings management and validation.
"""

from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv
from typing import Optional
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Get the app's root directory
APP_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    """Application settings."""

    # Flask settings
    FLASK_APP: str = "hyperblend.app"
    FLASK_ENV: str = "development"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    STATIC_FOLDER: str = str(APP_DIR / "web" / "static")
    TEMPLATE_FOLDER: str = str(APP_DIR / "web" / "templates")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "5001"))

    # Neo4j settings
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "hyperblend")
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = int(
        os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "50")
    )
    NEO4J_MAX_CONNECTION_LIFETIME: int = int(
        os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "3600")
    )  # 1 hour

    # API settings
    API_PREFIX: str = "/api/v1"
    DRUGBANK_API_KEY: Optional[str] = os.getenv("DRUGBANK_API_KEY")

    class Config:
        case_sensitive = True

    def to_dict(self):
        """Convert settings to a dictionary."""
        return {
            key: getattr(self, key)
            for key in self.__annotations__
            if not key.startswith("_")
        }


# Create settings instance
settings = Settings()
