"""Staged pipeline orchestrator.

A small, explicit state machine over typed nodes. It mirrors the design's
LangGraph node structure (ingest -> extract -> generate -> compile) without the
dependency, so the POC is trivially unit-testable. The swap to LangGraph is an
orchestration-layer change only: each ``_node_*`` becomes a graph node operating
on ``PipelineState``, and the linear ``run`` becomes graph edges (plus the
coverage refinement loop in Phase 4).
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from qa_architect.agents import BehavioralTestGenerator, RequirementExtractor
from qa_architect.config import Settings
from qa_architect.ingestion.models import DocumentTree
from qa_architect.ir import (
    CoverageDimension,
    DocMetadata,
    EvaluationBlueprint,
    Provenance,
    TraceLink,
    VerifiedBy,
)
from qa_architect.llm.base import LLMClient
from qa_architect.llm.factory import build_llm_client
from qa_architect.orchestration.state import PipelineState

Node = Callable[[PipelineState], None]


class Pipeline:
    def __init__(self, llm: LLMClient, settings: Settings | None = None) -> None:
        self.llm = llm
        self.settings = settings or Settings()
        self.extractor = RequirementExtractor(llm)
        self.test_generator = BehavioralTestGenerator(llm)

    # ---- public API -------------------------------------------------------
    def run(self, document: DocumentTree, *, run_id: str | None = None) -> EvaluationBlueprint:
        state = PipelineState(
            run_id=run_id or f"run-{uuid.uuid4().hex[:12]}",
            document=document,
            config_snapshot={
                "provider": self.llm.provider_name,
                "model": self.llm.model,
            },
        )
        # Phase 0-2 node sequence. Phases 3-4 add fan-out generators, critic,
        # and the coverage-driven refinement loop here.
        for name, node in self._nodes():
            self._run_node(state, name, node)
        return self._compile(state)

    # ---- node registry ----------------------------------------------------
    def _nodes(self) -> list[tuple[str, Node]]:
        return [
            ("extract_requirements", self._node_extract),
            ("generate_behavioral_tests", self._node_generate_tests),
            ("build_trace_links", self._node_trace_links),
        ]

    def _run_node(self, state: PipelineState, name: str, node: Node) -> None:
        start = time.perf_counter()
        node(state)
        elapsed = (time.perf_counter() - start) * 1000
        state.nodes_run.append(name)
        state.log(f"node={name} elapsed_ms={elapsed:.1f}")

    # ---- nodes ------------------------------------------------------------
    def _node_extract(self, state: PipelineState) -> None:
        assert state.document is not None
        state.requirements = self.extractor.run(state.document)
        state.log(f"extracted {len(state.requirements)} requirements")

    def _node_generate_tests(self, state: PipelineState) -> None:
        state.tests = self.test_generator.run(state.requirements)
        state.log(f"generated {len(state.tests)} behavioral tests")

    def _node_trace_links(self, state: PipelineState) -> None:
        """Self-tag trace links for the 'tested' dimension (primary signal)."""
        links: list[TraceLink] = []
        valid_ids = {r.id for r in state.requirements}
        for test in state.tests:
            for req_id in test.requirement_ids:
                if req_id not in valid_ids:
                    continue
                links.append(
                    TraceLink(
                        requirement_id=req_id,
                        artifact_id=test.id,
                        artifact_type="behavioral_test",
                        coverage_dimension=CoverageDimension.TESTED,
                        confidence=1.0,
                        verified_by=VerifiedBy.SELF_TAG,
                    )
                )
        state.trace_links = links
        state.log(f"built {len(links)} trace links")

    # ---- compile ----------------------------------------------------------
    def _compile(self, state: PipelineState) -> EvaluationBlueprint:
        doc = state.document
        assert doc is not None
        return EvaluationBlueprint(
            generation_run_id=state.run_id,
            doc_metadata=DocMetadata(
                doc_id=doc.doc_id,
                source_name=doc.source_name,
                media_type=doc.media_type,
                section_count=len(doc.sections),
                char_count=doc.char_count,
            ),
            requirements=state.requirements,
            tests=state.tests,
            trace_links=state.trace_links,
            coverage=state.coverage,  # populated in Phase 4
            provenance=Provenance(
                llm_provider=self.llm.provider_name,
                llm_model=self.llm.model,
                pipeline_nodes=state.nodes_run,
                notes=state.logs,
            ),
        )


def build_pipeline(settings: Settings | None = None) -> Pipeline:
    settings = settings or Settings()
    llm = build_llm_client(settings)
    return Pipeline(llm, settings)
