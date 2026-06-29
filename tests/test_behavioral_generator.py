"""Phase 2 — behavioral test generation."""

from qa_architect.agents import BehavioralTestGenerator, RequirementExtractor
from qa_architect.ir import RequirementType, TestCategory
from qa_architect.llm import StubLLMClient


def _gen(sample_doc):
    reqs = RequirementExtractor(StubLLMClient()).run(sample_doc)
    tests = BehavioralTestGenerator(StubLLMClient()).run(reqs)
    return reqs, tests


def test_every_requirement_has_at_least_one_test(sample_doc):
    reqs, tests = _gen(sample_doc)
    covered = {rid for t in tests for rid in t.requirement_ids}
    assert {r.id for r in reqs} <= covered


def test_test_ids_unique(sample_doc):
    _, tests = _gen(sample_doc)
    ids = [t.id for t in tests]
    assert len(set(ids)) == len(ids)
    assert all(t.id.startswith("TEST-") for t in tests)


def test_positive_and_negative_present(sample_doc):
    _, tests = _gen(sample_doc)
    cats = {t.category for t in tests}
    assert TestCategory.POSITIVE in cats
    assert TestCategory.NEGATIVE in cats


def test_guardrails_get_counter_examples(sample_doc):
    reqs, tests = _gen(sample_doc)
    guardrail_ids = {r.id for r in reqs if r.type is RequirementType.GUARDRAIL}
    counter_req_ids = {
        rid
        for t in tests
        if t.category is TestCategory.COUNTER_EXAMPLE
        for rid in t.requirement_ids
    }
    assert guardrail_ids <= counter_req_ids


def test_self_tags_reference_valid_requirements(sample_doc):
    reqs, tests = _gen(sample_doc)
    valid = {r.id for r in reqs}
    for t in tests:
        assert t.requirement_ids
        assert all(rid in valid for rid in t.requirement_ids)
        assert t.assertion.value
