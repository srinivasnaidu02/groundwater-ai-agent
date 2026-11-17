"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    APP_NAME: str = "Groundwater AI Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./data/database/groundwater.db"
    DATABASE_PATH: str = "./data/database/groundwater.db"

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8000,http://127.0.0.1:8000"

    LLM_PROVIDER: str = "rule_based"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    DATA_DIR: str = "./data/raw"
    PROCESSED_DIR: str = "./data/processed"

    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def cors_origins(self) -> list:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()

