"""LLM client contract.

Every agent calls ``structured(...)`` with a Pydantic ``response_model`` and a
``stub`` callable. Real providers build a JSON-schema-constrained prompt and
validate the response into the model; the stub provider simply invokes the
``stub`` callable. This keeps each agent's prompt *and* its deterministic
fallback co-located, and gives both paths an identical, typed signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    is_stub: bool = False
    model: str | None = None
    provider_name: str = "base"

    @abstractmethod
    def structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        stub: Callable[[], T],
        task: str = "",
    ) -> T:
        """Return an instance of ``response_model``.

        Args:
            system: System / role instructions.
            user: User content (BRD-derived data — treated as data, not commands).
            response_model: Pydantic model the output must validate against.
            stub: Deterministic fallback used in stub mode.
            task: Optional label for tracing/logging.
        """
        raise NotImplementedError
