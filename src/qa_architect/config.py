"""Runtime configuration.

Settings are read from environment variables (and an optional .env file). Field
names map directly to upper-case env vars, e.g. ``llm_model`` <- ``LLM_MODEL``.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider: "auto" | "stub" | "litellm"
    llm_provider: str = "auto"
    llm_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 8192

    # Standard provider env var names are honoured directly.
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    data_dir: str = "data"

    # Coverage refinement loop bound (used from Phase 4 onward).
    max_refine_iters: int = 2

    def resolve_provider(self) -> str:
        """Resolve the concrete provider, honouring 'auto'."""
        provider = (self.llm_provider or "auto").lower()
        if provider != "auto":
            return provider
        if self.anthropic_api_key or self.openai_api_key:
            return "litellm"
        return "stub"


def get_settings() -> Settings:
    return Settings()
