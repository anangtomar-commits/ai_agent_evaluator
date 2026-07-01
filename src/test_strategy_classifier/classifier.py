import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from db import pipeline_runs
from extractor.extractor import extract_sections
from output_store import save_phase_output
from requirements_extractor.extractor import extract_requirements
from requirements_extractor.models import SectionRequirements
from prompts.test_strategy_classifier import SYSTEM_PROMPT, USER_TEMPLATE

load_dotenv()

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"

_VALID_STRATEGIES = {
    "Conversational",
    "Performance",
    "Security",
    "BusinessKPI",
    "Infrastructure",
}

_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "classify_strategies",
        "description": "Return the test strategy classification for each requirement.",
        "parameters": {
            "type": "object",
            "properties": {
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "The requirement ID, e.g. REQ-000001.",
                            },
                            "test_strategy": {
                                "type": "string",
                                "enum": [
                                    "Conversational",
                                    "Performance",
                                    "Security",
                                    "BusinessKPI",
                                    "Infrastructure",
                                ],
                            },
                        },
                        "required": ["id", "test_strategy"],
                    },
                }
            },
            "required": ["classifications"],
        },
    },
}


def _build_client() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to your .env file or environment."
        )
    return OpenAI(api_key=api_key, base_url=_GROQ_BASE_URL)


def _call_llm(client: OpenAI, requirements_json: str, model: str) -> dict[str, str]:
    """Sends all requirements in one batch; returns {req_id: strategy} map."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(requirements_json=requirements_json)},
        ],
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "classify_strategies"}},
        max_tokens=4096,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    classifications = json.loads(tool_call.function.arguments).get("classifications", [])
    return {c["id"]: c["test_strategy"] for c in classifications}


def classify_strategies(
    section_requirements: list[SectionRequirements],
    model: str = _DEFAULT_MODEL,
) -> list[SectionRequirements]:
    """
    Accepts the output of the requirements extractor, adds test_strategy to every
    Requirement, and returns the updated structure.
    """
    # Flatten to a simple list for the LLM — only send the fields it needs
    flat_reqs = [
        {
            "id": req.id,
            "statement": req.statement,
            "type": req.type,
            "domain": req.domain,
        }
        for sr in section_requirements
        for req in sr.requirements
    ]

    if not flat_reqs:
        return section_requirements

    client = _build_client()
    strategy_map = _call_llm(client, json.dumps(flat_reqs, indent=2), model)

    # Write test_strategy back onto each Requirement in place
    for sr in section_requirements:
        for req in sr.requirements:
            req.test_strategy = strategy_map.get(req.id)

    return section_requirements


def classify_from_file(
    file_path: str,
    original_name: str = None,
    model: str = _DEFAULT_MODEL,
    project_id: str = None,
    run_id: str = None,
) -> list[SectionRequirements]:
    """
    Full pipeline: text extraction → requirements extraction → strategy classification.
    Saves output to outputs/test_strategy_classifier/.
    """
    path = Path(file_path)
    file_name = original_name or path.name

    # Phase 2: requirements extraction
    section_requirements = extract_requirements(
        file_path, original_name, model, project_id, run_id
    )

    # Phase 3: strategy classification
    classified = classify_strategies(section_requirements, model)

    save_phase_output(
        phase="test_strategy_classifier",
        doc_name=file_name,
        data=[sr.model_dump() for sr in classified],
        project_id=project_id,
    )

    if run_id:
        pipeline_runs.update_output(
            run_id, "requirements", [sr.model_dump() for sr in classified]
        )

    return classified
