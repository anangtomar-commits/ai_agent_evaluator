"""Phase 1 — requirement extraction (stub heuristics)."""

from qa_architect.agents import RequirementExtractor
from qa_architect.ir import RequirementType
from qa_architect.llm import StubLLMClient


def _extract(sample_doc):
    return RequirementExtractor(StubLLMClient()).run(sample_doc)


def test_extracts_multiple_requirements(sample_doc):
    reqs = _extract(sample_doc)
    assert len(reqs) >= 8


def test_ids_are_unique_and_sequential(sample_doc):
    reqs = _extract(sample_doc)
    ids = [r.id for r in reqs]
    assert ids == [f"REQ-{i:03d}" for i in range(1, len(reqs) + 1)]
    assert len(set(ids)) == len(ids)


def test_covers_key_types(sample_doc):
    types = {r.type for r in _extract(sample_doc)}
    assert RequirementType.TONE in types
    assert RequirementType.GUARDRAIL in types
    assert RequirementType.COMPLIANCE in types
    assert RequirementType.SUCCESS_CRITERION in types


def test_guardrails_get_risk_tags(sample_doc):
    reqs = _extract(sample_doc)
    guardrails = [r for r in reqs if r.type is RequirementType.GUARDRAIL]
    assert guardrails
    assert all(r.risk_tags for r in guardrails)


def test_source_provenance_present(sample_doc):
    reqs = _extract(sample_doc)
    assert all(r.source_span is not None for r in reqs)
    assert all(r.source_span.doc_id == sample_doc.doc_id for r in reqs)
