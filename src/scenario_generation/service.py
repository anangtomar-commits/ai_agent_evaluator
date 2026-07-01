import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from output_store import save_phase_output
from requirements_extractor.models import Requirement, SectionRequirements
from scenario_generation.models import TestPlan
from scenario_generation.planner import ScenarioPlanner
from test_strategy_classifier.classifier import classify_from_file

load_dotenv()

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Placeholder used for fields not yet produced for unsupported strategies.
_NOT_AVAILABLE = "NA"


def _build_client() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to your .env file or environment."
        )
    return OpenAI(api_key=api_key, base_url=_GROQ_BASE_URL)


def _placeholder_plan(requirement: Requirement) -> TestPlan:
    """
    Builds a TestPlan for a requirement whose strategy has no generator yet.
    Known fields are kept; everything not produced in this phase is marked "NA"
    and the scenarios list is empty.
    """
    return TestPlan(
        requirement_id=requirement.id,
        requirement=requirement,
        strategy=requirement.test_strategy or _NOT_AVAILABLE,
        rationale=_NOT_AVAILABLE,
        scenarios=[],
    )


class ScenarioGenerator:
    """
    Orchestrates scenario generation across all requirements.

    For every requirement it asks the planner for a TestPlan. Strategies without
    a registered generator (Performance, Security, Infrastructure, BusinessKPI)
    get a placeholder plan with "NA" fields and no scenarios, so they still
    appear in the output. Only conversational requirements get real scenarios.
    """

    def __init__(self, model: str = _DEFAULT_MODEL):
        self.client = _build_client()
        self.planner = ScenarioPlanner(self.client, model)

    def generate(self, section_requirements: list[SectionRequirements]) -> list[TestPlan]:
        plans: list[TestPlan] = []
        for sr in section_requirements:
            for req in sr.requirements:
                result = self.planner.plan(req)
                if result is NotImplemented:
                    # No generator for this strategy yet — emit an NA placeholder.
                    plans.append(_placeholder_plan(req))
                    continue
                plans.append(result)
        return plans


def generate_scenarios(
    section_requirements: list[SectionRequirements],
    model: str = _DEFAULT_MODEL,
) -> list[TestPlan]:
    """Generates test plans for already-classified requirements."""
    return ScenarioGenerator(model).generate(section_requirements)


def generate_from_file(
    file_path: str,
    original_name: str = None,
    model: str = _DEFAULT_MODEL,
) -> list[TestPlan]:
    """
    Full pipeline: text extraction → requirements extraction → strategy
    classification → scenario generation. Saves output to
    outputs/scenario_generator/.
    """
    path = Path(file_path)
    file_name = original_name or path.name

    classified = classify_from_file(file_path, original_name, model)
    plans = generate_scenarios(classified, model)

    save_phase_output(
        phase="scenario_generator",
        doc_name=file_name,
        data=[plan.model_dump() for plan in plans],
    )

    return plans
