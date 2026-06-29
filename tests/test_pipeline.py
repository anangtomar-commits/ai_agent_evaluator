"""Phases 0-2 — end-to-end pipeline (stub mode)."""

from qa_architect.ir import EvaluationBlueprint


def test_pipeline_produces_blueprint(blueprint):
    assert isinstance(blueprint, EvaluationBlueprint)
    assert blueprint.generation_run_id == "run-test"
    assert blueprint.requirements
    assert blueprint.tests
    assert blueprint.coverage is None  # populated from Phase 4


def test_provenance_records_nodes(blueprint):
    nodes = blueprint.provenance.pipeline_nodes
    assert "extract_requirements" in nodes
    assert "generate_behavioral_tests" in nodes
    assert "build_trace_links" in nodes
    assert blueprint.provenance.llm_provider == "stub"


def test_trace_links_reference_valid_ids(blueprint):
    valid = {r.id for r in blueprint.requirements}
    test_ids = {t.id for t in blueprint.tests}
    assert blueprint.trace_links
    for link in blueprint.trace_links:
        assert link.requirement_id in valid
        assert link.artifact_id in test_ids
        assert link.coverage_dimension.value == "tested"


def test_doc_metadata_populated(blueprint):
    assert blueprint.doc_metadata.section_count > 0
    assert blueprint.doc_metadata.char_count > 0
