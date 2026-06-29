"""Mutable pipeline state — the evolving aggregate passed between nodes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from qa_architect.ingestion.models import DocumentTree
from qa_architect.ir import (
    BehavioralTest,
    CoverageReport,
    Metric,
    RedTeamScenario,
    Requirement,
    TraceLink,
)


class PipelineState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    document: DocumentTree | None = None
    requirements: list[Requirement] = Field(default_factory=list)
    tests: list[BehavioralTest] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    red_team: list[RedTeamScenario] = Field(default_factory=list)
    trace_links: list[TraceLink] = Field(default_factory=list)
    coverage: CoverageReport | None = None

    nodes_run: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    config_snapshot: dict = Field(default_factory=dict)

    def log(self, message: str) -> None:
        self.logs.append(message)
