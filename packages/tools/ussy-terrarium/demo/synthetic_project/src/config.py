"""Configuration management."""

import os
from typing import Any, Optional


class Config:
    """Application configuration."""

    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///app.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # Email settings
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Cache settings
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 300

    # API settings
    API_RATE_LIMIT: int = 100
    API_RATE_WINDOW: int = 3600

    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables."""
        cls.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        cls.DATABASE_URL = os.getenv("DATABASE_URL", cls.DATABASE_URL)
        cls.SECRET_KEY = os.getenv("SECRET_KEY", cls.SECRET_KEY)
        cls.SMTP_HOST = os.getenv("SMTP_HOST", cls.SMTP_HOST)
        cls.SMTP_PORT = int(os.getenv("SMTP_PORT", cls.SMTP_PORT))
        cls.REDIS_URL = os.getenv("REDIS_URL")
        cls.API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", cls.API_RATE_LIMIT))

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return getattr(cls, key, default)


# Load configuration on import
Config.load_from_env()
