# hyperblend/app/config/settings.py

import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Base configuration."""

    # Get the application root directory
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    # Neo4j settings
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "your_password"

    # Flask settings
    FLASK_APP = "hyperblend.app"
    FLASK_ENV = "development"
    DEBUG = True
    SECRET_KEY = "your-secret-key-here"

    # Static files
    STATIC_FOLDER = str(BASE_DIR / "app" / "web" / "static")
    TEMPLATE_FOLDER = str(BASE_DIR / "app" / "web" / "templates")

    # API keys
    PUBCHEM_API_KEY = None
    CHEMBL_API_KEY = None
    DRUGBANK_API_KEY = None

    # Database URL
    DATABASE_URL = "sqlite:///./hyperblend.db"

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "hyperblend.log"

    # Cache settings
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300

    # CORS settings
    CORS_ORIGINS = ["http://localhost:5000"]

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and not callable(getattr(cls, key))
        }


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    NEO4J_URI = "bolt://localhost:7688"  # Use different port for testing


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    # Override these with environment variables in production
    NEO4J_URI = os.getenv("NEO4J_URI", Config.NEO4J_URI)
    NEO4J_USER = os.getenv("NEO4J_USER", Config.NEO4J_USER)
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", Config.NEO4J_PASSWORD)
    SECRET_KEY = os.getenv("SECRET_KEY", Config.SECRET_KEY)


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


# Get current configuration
def get_config(env: str = None) -> Config:
    """Get configuration based on environment."""
    env = env or os.getenv("FLASK_ENV", "development")
    return config.get(env, config["default"])


# Create settings instance
settings = get_config()

# Ensure required directories exist
Path(settings.STATIC_FOLDER).mkdir(parents=True, exist_ok=True)
Path(settings.TEMPLATE_FOLDER).mkdir(parents=True, exist_ok=True)

# Configure logging
import logging
import sys

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)

# Create logger instance
logger = logging.getLogger(__name__)
