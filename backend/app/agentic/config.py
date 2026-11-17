"""Configuration for the Agentic & Generative AI layer using Pydantic Settings."""
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class AgenticSettings(BaseSettings):
    """Agentic AI configuration with multi-provider support."""

    LLM_PROVIDER: str = Field(default="gemini", description="gemini | openai | anthropic | mock")
    LLM_MODEL: Optional[str] = Field(default=None, description="Model override (e.g. gemini-2.5-flash, gpt-4o-mini)")

    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")

    AGENT_MAX_STEPS: int = Field(default=6, ge=1, le=20, description="Max tool execution steps per query")
    AGENT_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120, description="Overall agent execution timeout")
    LLM_TEMPERATURE: float = Field(default=0.2, ge=0.0, le=1.0, description="Sampling temperature for synthesis")
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

    @property
    def agentic_enabled(self) -> bool:
        return self.AGENTIC_ENABLED

    @property
    def agent_max_steps(self) -> int:
        return self.AGENT_MAX_STEPS

    @property
    def agent_timeout_seconds(self) -> int:
        return self.AGENT_TIMEOUT_SECONDS

    @property
    def llm_temperature(self) -> float:
        return self.LLM_TEMPERATURE

    @property
    def llm_model(self) -> str:
        return self.get_effective_model()

    @property
    def llm_provider(self) -> str:
        return self.LLM_PROVIDER

    def get_effective_model(self) -> str:
        """Return the default model name for the selected provider if not overridden."""
        if self.LLM_MODEL:
            return self.LLM_MODEL
        provider = (self.LLM_PROVIDER or "gemini").lower()
        if provider == "gemini":
            return "gemini-2.5-flash"
        elif provider == "openai":
            return "gpt-4o-mini"
        elif provider == "anthropic":
            return "claude-3-5-haiku-20241022"
        return "mock-agent-model"

    def has_api_key(self) -> bool:
        """Check whether the active provider has a valid non-empty API key."""
        provider = (self.LLM_PROVIDER or "").lower()
        if provider == "mock":
            return True
        if provider == "gemini":
            return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())
        if provider == "openai":
            return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())
        if provider == "anthropic":
            return bool(self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY.strip())
        return False


agentic_settings = AgenticSettings()
AgenticConfig = AgenticSettings


def get_agentic_settings() -> AgenticSettings:
    """Return cached or refreshed agentic settings."""
    return agentic_settings
