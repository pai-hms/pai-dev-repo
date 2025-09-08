"""Configuration module for the SQL Agent application."""

import os
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database Configuration
    database_url: str = "postgresql://postgres:password@localhost:5432/pai_sql_agent"
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_db: str = "pai_sql_agent"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    
    # SGIS API Configuration
    sgis_api_key: Optional[str] = None
    sgis_secret_key: Optional[str] = None
    
    # Application Configuration
    debug: bool = True
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
