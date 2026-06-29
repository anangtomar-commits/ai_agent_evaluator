"""Real multi-provider LLM client backed by LiteLLM.

LiteLLM is imported lazily so the package (and the stub-mode test suite) does not
require it to be installed.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from qa_architect.llm.base import LLMClient

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(content: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from model output."""
    text = content.strip()
    # Strip ```json ... ``` fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        text = re.sub(r"^json\s*", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(text)
        candidate = match.group(0) if match else text
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        try:
            from json_repair import repair_json  # type: ignore[import]
            repaired = repair_json(candidate, return_objects=True)
            if isinstance(repaired, dict):
                return repaired
        except ImportError:
            pass
        raise


class LiteLLMClient(LLMClient):
    is_stub = False
    provider_name = "litellm"

    def __init__(
        self,
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> None:
        import litellm  # noqa: F401  (lazy, optional dependency)

        self._litellm = litellm
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        stub: Callable[[], T],
        task: str = "",
    ) -> T:
        schema = response_model.model_json_schema()
        system_prompt = (
            f"{system}\n\n"
            "Return ONLY a single JSON object that conforms to this JSON Schema. "
            "Do not include prose or markdown fences.\n"
            f"JSON Schema:\n{json.dumps(schema)}"
        )
        response = self._litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        data = _extract_json(content)
        return response_model.model_validate(data)
