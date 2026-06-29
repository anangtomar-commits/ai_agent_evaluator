"""Build the configured LLM client from settings."""

from __future__ import annotations

import os

from qa_architect.config import Settings
from qa_architect.llm.base import LLMClient
from qa_architect.llm.stub import StubLLMClient


def build_llm_client(settings: Settings) -> LLMClient:
    provider = settings.resolve_provider()
    if provider == "stub":
        return StubLLMClient()

    if provider == "litellm":
        # Surface configured keys to the environment LiteLLM reads from.
        if settings.anthropic_api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
        if settings.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

        from qa_architect.llm.litellm_client import LiteLLMClient

        return LiteLLMClient(
            settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    raise ValueError(f"Unknown LLM provider: {provider!r}")
