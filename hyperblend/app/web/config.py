# hyperblend/app/web/config.py

import os
import logging


class BaseConfig:
    """Base configuration for the application."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_key_for_hyperblend")
    DEBUG = False
    TESTING = False
    LOG_LEVEL = logging.INFO

    # Database settings
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")

    # Admin settings
    ADMIN_PASSWORD = os.environ.get("HYPERBLEND_ADMIN_PASSWORD", "hyperblend_admin")
    ADMIN_TOKEN = os.environ.get("HYPERBLEND_ADMIN_TOKEN", "admin_token_for_hyperblend")


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    LOG_LEVEL = logging.DEBUG
    BYPASS_ADMIN_AUTH = os.environ.get("BYPASS_ADMIN_AUTH", "true").lower() == "true"


class TestingConfig(BaseConfig):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    LOG_LEVEL = logging.DEBUG
    BYPASS_ADMIN_AUTH = True

    # Test database settings
    NEO4J_URI = os.environ.get("TEST_NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("TEST_NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("TEST_NEO4J_PASSWORD", "neo4j")


class ProductionConfig(BaseConfig):
    """Production configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = False
    TESTING = False
    LOG_LEVEL = logging.WARNING
    BYPASS_ADMIN_AUTH = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name):
    """Get configuration class by name."""
    return config.get(config_name, config["default"])
