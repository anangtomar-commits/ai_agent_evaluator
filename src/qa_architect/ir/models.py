"""Pydantic v2 models for the Evaluation Blueprint IR (design doc, Section 3)."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from qa_architect.ir.enums import (
    AssertionKind,
    AttackClass,
    CoverageDimension,
    MeasurementMethod,
    MetricLevel,
    Priority,
    RequirementType,
    TestCategory,
    VerifiedBy,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceSpan(BaseModel):
    """Provenance link back into the source document."""

    doc_id: str
    section_id: str | None = None
    heading: str | None = None
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None


class Requirement(BaseModel):
    id: str
    type: RequirementType
    statement: str
    rationale: str | None = None
    source_span: SourceSpan | None = None
    priority: Priority = Priority.MEDIUM
    domain_tags: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    ambiguity_flag: bool = False


class Assertion(BaseModel):
    """How a behavioral test's pass/fail is decided."""

    kind: AssertionKind = AssertionKind.LLM_RUBRIC
    value: str
    metric_id: str | None = None


class BehavioralTest(BaseModel):
    id: str
    requirement_ids: list[str]
    category: TestCategory
    input: str
    conversation: list[dict] | None = None
    expected_behavior: str
    assertion: Assertion
    rationale: str | None = None


class Metric(BaseModel):
    id: str
    requirement_ids: list[str]
    level: MetricLevel
    name: str
    definition: str
    measurement_method: MeasurementMethod
    data_required: list[str] = Field(default_factory=list)
    target_threshold: str | None = None
    framework_hint: str | None = None


class RedTeamScenario(BaseModel):
    id: str
    requirement_ids: list[str]
    attack_class: AttackClass
    technique: str
    attack_prompt: str
    expected_safe_behavior: str
    severity: Priority = Priority.MEDIUM
    likelihood: Priority = Priority.MEDIUM
    business_impact: str | None = None
    priority_score: float = 0.0


class TraceLink(BaseModel):
    requirement_id: str
    artifact_id: str
    artifact_type: str  # "behavioral_test" | "metric" | "red_team"
    coverage_dimension: CoverageDimension
    confidence: float = 1.0
    verified_by: VerifiedBy = VerifiedBy.SELF_TAG


class RequirementCoverage(BaseModel):
    requirement_id: str
    tested: bool = False
    measured: bool = False
    adversarially_probed: bool = False
    score: float = 0.0
    notes: list[str] = Field(default_factory=list)


class CoverageReport(BaseModel):
    per_requirement: list[RequirementCoverage] = Field(default_factory=list)
    aggregate_score: float = 0.0
    tested_pct: float = 0.0
    measured_pct: float = 0.0
    probed_pct: float = 0.0
    gaps: list[str] = Field(default_factory=list)
    uncovered_requirement_ids: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class DocMetadata(BaseModel):
    doc_id: str
    source_name: str
    media_type: str
    section_count: int = 0
    char_count: int = 0


class Provenance(BaseModel):
    generated_at: datetime = Field(default_factory=_utcnow)
    llm_provider: str = "stub"
    llm_model: str | None = None
    pipeline_nodes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvaluationBlueprint(BaseModel):
    """Root aggregate — the single evolving artifact of the pipeline."""

    generation_run_id: str
    version: str = "0.1"
    doc_metadata: DocMetadata
    requirements: list[Requirement] = Field(default_factory=list)
    tests: list[BehavioralTest] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    red_team: list[RedTeamScenario] = Field(default_factory=list)
    trace_links: list[TraceLink] = Field(default_factory=list)
    coverage: CoverageReport | None = None
    provenance: Provenance = Field(default_factory=Provenance)

    def requirement_index(self) -> dict[str, Requirement]:
        return {r.id: r for r in self.requirements}
