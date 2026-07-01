import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from extractor.extractor import extract_sections
from output_store import save_phase_output
from requirements_extractor.models import Requirement, SectionRequirements
from prompts.requirements_extractor import SYSTEM_PROMPT, USER_TEMPLATE

load_dotenv()

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"

_SECTION_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")
_CODE_PATTERN = re.compile(r"^([A-Z]+-[A-Z0-9]+)\s+(.+)$")

# Fields the LLM populates. ID and source-location fields are assigned by the system.
_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "extract_requirements",
        "description": "Return the list of structured requirements extracted from a BRD section.",
        "parameters": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_requirement": {
                                "type": ["string", "null"],
                                "description": "Requirement ID exactly as written in the BRD (e.g. FR-A01, G-01), or null if absent.",
                            },
                            "type": {
                                "type": "string",
                                "enum": [
                                    "Functional",
                                    "NonFunctional",
                                    "BusinessRule",
                                    "Constraint",
                                    "Assumption",
                                    "Goal",
                                    "Risk",
                                    "AcceptanceCriteria",
                                ],
                                "description": "What kind of requirement this is.",
                            },
                            "domain": {
                                "type": "string",
                                "enum": [
                                    "API",
                                    "Security",
                                    "Performance",
                                    "Language",
                                    "Logging",
                                    "Deployment",
                                    "UI",
                                    "DataManagement",
                                    "Integration",
                                    "Authentication",
                                    "Notification",
                                    "ErrorHandling",
                                ],
                                "description": "Which system domain / area this requirement belongs to.",
                            },
                            "statement": {
                                "type": "string",
                                "description": "Normalised, atomic requirement statement starting with 'The system must/should/may …'",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["High", "Medium", "Low"],
                            },
                            "testable": {"type": "boolean"},
                            "acceptance_criteria": {
                                "type": "string",
                                "description": "Concrete, measurable pass/fail condition for deepeval / promptfoo.",
                            },
                            "ambiguity_flag": {"type": "boolean"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Lowercase kebab-case labels for test-suite filtering.",
                            },
                            "source_text": {
                                "type": ["string", "null"],
                                "description": "Verbatim BRD excerpt (≤ 200 chars) this requirement was drawn from.",
                            },
                        },
                        "required": [
                            "source_requirement",
                            "type",
                            "domain",
                            "statement",
                            "priority",
                            "testable",
                            "acceptance_criteria",
                            "ambiguity_flag",
                            "tags",
                            "source_text",
                        ],
                    },
                }
            },
            "required": ["requirements"],
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


def _parse_heading(heading: str) -> tuple[str | None, str]:
    """Splits '5.2 Answer Mode' → ('5.2', 'Answer Mode'), 'FR-A01 Title' → ('FR-A01', 'Title')."""
    m = _SECTION_PATTERN.match(heading.strip())
    if m:
        return m.group(1), m.group(2).strip()
    m = _CODE_PATTERN.match(heading.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return None, heading.strip()


def _call_llm(client: OpenAI, heading: str, text: str, model: str) -> list[dict]:
    """Calls Groq with tool use and returns the raw LLM-extracted requirements list."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(heading=heading, text=text)},
        ],
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "extract_requirements"}},
    )

    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments).get("requirements", [])


def _build_requirements(
    raw_reqs: list[dict],
    start: int,
    section_id: str | None,
    page_start: int | None,
) -> list[Requirement]:
    """
    Merges LLM-extracted fields with system-assigned fields (id, source traceability)
    and validates the result against the Pydantic model.
    IDs are globally unique 6-digit zero-padded: REQ-000001, REQ-000002, …
    """
    result = []
    for i, r in enumerate(raw_reqs, start=start):
        req = Requirement(
            id=f"REQ-{i:06d}",
            source_section=section_id,
            source_page=page_start,
            **r,
        )
        result.append(req)
    return result


def extract_requirements(
    file_path: str,
    original_name: str = None,
    model: str = _DEFAULT_MODEL,
    project_id: str = None,
) -> list[SectionRequirements]:
    """
    Full pipeline: extract sections → call Groq per section → return structured requirements.
    Output is also persisted to outputs/requirements_extractor/.
    """
    path = Path(file_path)
    file_name = original_name or path.name

    sections = extract_sections(file_path, original_name, project_id)

    client = _build_client()
    results: list[SectionRequirements] = []
    req_counter = 1  # global across all sections — guarantees unique IDs

    for section in sections:
        heading: str = section.get("heading", "")
        text: str = section.get("text", "").strip()

        if not text:
            continue

        section_id, section_title = _parse_heading(heading)

        raw_reqs = _call_llm(client, heading, text, model)

        if not raw_reqs:
            continue

        requirements = _build_requirements(
            raw_reqs,
            start=req_counter,
            section_id=section_id,
            page_start=section.get("page_start"),
        )
        req_counter += len(requirements)

        results.append(
            SectionRequirements(
                section_id=section_id,
                section_title=section_title,
                page_start=section.get("page_start"),
                page_end=section.get("page_end"),
                requirements=requirements,
            )
        )

    save_phase_output(
        phase="requirements_extractor",
        doc_name=file_name,
        data=[sr.model_dump() for sr in results],
        project_id=project_id,
    )

    return results
