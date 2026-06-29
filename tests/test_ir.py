"""Phase 0 — IR schema validation and round-tripping."""

import pytest
from pydantic import ValidationError

from qa_architect.ir import (
    Assertion,
    AssertionKind,
    BehavioralTest,
    DocMetadata,
    EvaluationBlueprint,
    Priority,
    Requirement,
    RequirementType,
    TestCategory,
)


def test_requirement_defaults():
    req = Requirement(id="REQ-001", type=RequirementType.GUARDRAIL, statement="No PII.")
    assert req.priority is Priority.MEDIUM
    assert req.domain_tags == []
    assert req.ambiguity_flag is False


def test_enum_validation_rejects_bad_type():
    with pytest.raises(ValidationError):
        Requirement(id="REQ-001", type="not-a-type", statement="x")


def test_blueprint_json_roundtrip():
    bp = EvaluationBlueprint(
        generation_run_id="run-1",
        doc_metadata=DocMetadata(doc_id="d1", source_name="brd.md", media_type="text/markdown"),
        requirements=[Requirement(id="REQ-001", type=RequirementType.TONE, statement="Be warm.")],
        tests=[
            BehavioralTest(
                id="TEST-001",
                requirement_ids=["REQ-001"],
                category=TestCategory.POSITIVE,
                input="hi",
                expected_behavior="agent is warm",
                assertion=Assertion(kind=AssertionKind.LLM_RUBRIC, value="warm tone"),
            )
        ],
    )
    restored = EvaluationBlueprint.model_validate_json(bp.model_dump_json())
    assert restored.generation_run_id == "run-1"
    assert restored.requirement_index()["REQ-001"].type is RequirementType.TONE
    assert restored.tests[0].assertion.kind is AssertionKind.LLM_RUBRIC
