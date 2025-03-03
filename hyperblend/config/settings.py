from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Neo4j settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "your_password"

    # Flask settings
    FLASK_APP: str = "hyperblend.app"
    FLASK_ENV: str = "development"
    FLASK_DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-here"

    # API keys
    PUBCHEM_API_KEY: Optional[str] = None
    CHEMBL_API_KEY: Optional[str] = None
    DRUGBANK_API_KEY: Optional[str] = None

    # Database URL
    DATABASE_URL: str = "bolt://localhost:7687"

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "hyperblend.log"

    # COCONUT credentials
    COCONUT_EMAIL: Optional[str] = None
    COCONUT_PASSWORD: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
