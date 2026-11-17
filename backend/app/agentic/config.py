"""Agentic AI configuration with Pydantic BaseSettings."""
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class AgenticSettings(BaseSettings):
    """Configuration for Agentic AI LLM orchestration."""

    LLM_PROVIDER: Literal["gemini", "openai", "anthropic", "mock"] = Field(
        default="mock",
        description="LLM provider: gemini | openai | anthropic | mock"
    )
    LLM_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Default model name for LLM provider"
    )

    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")

    AGENT_MAX_STEPS: int = Field(default=6, ge=1, le=20, description="Max tool execution steps")
    AGENT_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120, description="Agent execution timeout")
    LLM_TEMPERATURE: float = Field(default=0.2, ge=0.0, le=1.0, description="Sampling temperature")
    AGENTIC_ENABLED: bool = Field(default=True, description="Master switch for agentic functionality")

    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).resolve().parents[3] / ".env"),
            str(Path(__file__).resolve().parents[2] / ".env"),
            ".env",
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def has_api_key(self) -> bool:
        """Check if active provider has an API key configured."""
        p = self.LLM_PROVIDER.lower()
        if p == "mock":
            return True
        if p == "gemini":
            return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())
        if p == "openai":
            return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())
        if p == "anthropic":
            return bool(self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY.strip())
        return False


agentic_settings = AgenticSettings()
AgenticConfig = AgenticSettings


def get_agentic_settings() -> AgenticSettings:
    """Return active agentic settings instance."""
    return agentic_settings
