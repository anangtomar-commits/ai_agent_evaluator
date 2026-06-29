"""Deterministic, offline LLM client.

Runs the agent-supplied ``stub`` callable instead of calling a model. This makes
the entire pipeline runnable and fully testable with no API key or network.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from pydantic import BaseModel

from qa_architect.llm.base import LLMClient

T = TypeVar("T", bound=BaseModel)


class StubLLMClient(LLMClient):
    is_stub = True
    provider_name = "stub"
    model = "stub"

    def structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        stub: Callable[[], T],
        task: str = "",
    ) -> T:
        result = stub()
        if not isinstance(result, response_model):
            raise TypeError(
                f"Stub for task '{task}' returned {type(result).__name__}, "
                f"expected {response_model.__name__}"
            )
        return result
