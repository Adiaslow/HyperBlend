"""Configuration settings for the HyperBlend system."""

from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # Neo4j settings
    NEO4J_URI: str = "neo4j://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "hyperblend"

    # API endpoints
    PUBCHEM_API_BASE: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    CHEMBL_API: str = "https://www.ebi.ac.uk/chembl/api/data"
    NAPRALERT_API: str = "https://napralert.org/api/v1"
    UNIPROT_API: str = "https://rest.uniprot.org"

    # API request settings
    REQUEST_TIMEOUT: int = 30  # seconds
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # seconds

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        """Pydantic settings config."""

        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the configuration


# Create global settings instance
settings = Settings()

__all__ = ["settings", "Settings"]
