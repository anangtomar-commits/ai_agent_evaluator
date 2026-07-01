import json

from openai import OpenAI

from prompts.conversational_scenario import SYSTEM_PROMPT, USER_TEMPLATE
from requirements_extractor.models import Requirement
from scenario_generation.generators.base_generator import BaseScenarioGenerator
from scenario_generation.models import Scenario, TestPlan
from scenario_generation.validator import (
    ScenarioValidationError,
    validate_scenarios,
)

# Deterministic scenario distribution — the application decides this, not the LLM.
_DISTRIBUTION: dict[str, int] = {
    "Positive": 1,
    "Negative": 1,
    "Boundary": 1,
    "Adversarial": 1,
}

_MAX_ATTEMPTS = 3

_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_scenarios",
        "description": "Return the conversational test scenarios for the requirement.",
        "parameters": {
            "type": "object",
            "properties": {
                "scenarios": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scenario_type": {
                                "type": "string",
                                "enum": ["Positive", "Negative", "Boundary", "Adversarial"],
                            },
                            "title": {
                                "type": "string",
                                "description": "Short, unique name for the scenario.",
                            },
                            "objective": {
                                "type": "string",
                                "description": "What this scenario verifies.",
                            },
                            "description": {
                                "type": "string",
                                "description": "The situation that should be tested (no prompts, no expected responses).",
                            },
                            "preconditions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "State that must hold before the scenario runs.",
                            },
                            "user_goal": {
                                "type": "string",
                                "description": "What the user is trying to achieve.",
                            },
                            "risk_area": {
                                "type": "string",
                                "description": "The risk this scenario guards against.",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["High", "Medium", "Low"],
                            },
                        },
                        "required": [
                            "scenario_type",
                            "title",
                            "objective",
                            "description",
                            "preconditions",
                            "user_goal",
                            "risk_area",
                            "priority",
                        ],
                    },
                }
            },
            "required": ["scenarios"],
        },
    },
}


def _build_user_prompt(requirement: Requirement) -> str:
    distribution_lines = "\n".join(
        f"  - {scenario_type}: {count}"
        for scenario_type, count in _DISTRIBUTION.items()
    )
    return USER_TEMPLATE.format(
        statement=requirement.statement,
        acceptance_criteria=requirement.acceptance_criteria,
        domain=requirement.domain,
        priority=requirement.priority,
        source_requirement=requirement.source_requirement or "N/A",
        total=sum(_DISTRIBUTION.values()),
        distribution_lines=distribution_lines,
    )


class ConversationScenarioGenerator(BaseScenarioGenerator):
    """Generates conversational test scenarios for a single requirement."""

    strategy = "Conversational"

    def generate(self, requirement: Requirement) -> TestPlan:
        user_prompt = _build_user_prompt(requirement)

        last_errors: list[str] = []
        for _ in range(_MAX_ATTEMPTS):
            raw_scenarios = self._call_llm(SYSTEM_PROMPT, user_prompt)
            scenarios = self._build_scenarios(raw_scenarios, requirement.id)

            errors = validate_scenarios(scenarios, requirement.id, _DISTRIBUTION)
            if not errors:
                return TestPlan(
                    requirement_id=requirement.id,
                    requirement=requirement,
                    strategy=self.strategy,
                    rationale=(
                        "Generated conversational scenarios covering positive, "
                        "negative, boundary and adversarial user interactions."
                    ),
                    scenarios=scenarios,
                )
            last_errors = errors

        raise ScenarioValidationError(
            f"Failed to generate valid scenarios for {requirement.id} "
            f"after {_MAX_ATTEMPTS} attempts: {'; '.join(last_errors)}"
        )

    def _call_llm(self, system_prompt: str, user_prompt: str) -> list[dict]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "function", "function": {"name": "generate_scenarios"}},
            max_tokens=4096,
        )
        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments).get("scenarios", [])

    def _build_scenarios(self, raw_scenarios: list[dict], requirement_id: str) -> list[Scenario]:
        """Merges LLM-generated content with system-assigned id and requirement_id."""
        scenarios: list[Scenario] = []
        for i, raw in enumerate(raw_scenarios, start=1):
            scenarios.append(
                Scenario(
                    id=f"{requirement_id}-SCN-{i:03d}",
                    requirement_id=requirement_id,
                    **raw,
                )
            )
        return scenarios
