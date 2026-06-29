"""Multi-provider LLM abstraction with a deterministic stub fallback."""

from qa_architect.llm.base import LLMClient
from qa_architect.llm.factory import build_llm_client
from qa_architect.llm.stub import StubLLMClient

__all__ = ["LLMClient", "StubLLMClient", "build_llm_client"]
