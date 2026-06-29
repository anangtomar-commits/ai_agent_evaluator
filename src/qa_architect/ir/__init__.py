"""Evaluation Blueprint Intermediate Representation (IR).

The IR is the framework-agnostic contract between generation and export. Export
adapters only ever see validated IR, never raw LLM output.
"""

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
from qa_architect.ir.models import (
    Assertion,
    BehavioralTest,
    CoverageReport,
    DocMetadata,
    EvaluationBlueprint,
    Metric,
    Provenance,
    RedTeamScenario,
    Requirement,
    RequirementCoverage,
    SourceSpan,
    TraceLink,
)

__all__ = [
    "AssertionKind",
    "AttackClass",
    "CoverageDimension",
    "MeasurementMethod",
    "MetricLevel",
    "Priority",
    "RequirementType",
    "TestCategory",
    "VerifiedBy",
    "Assertion",
    "BehavioralTest",
    "CoverageReport",
    "DocMetadata",
    "EvaluationBlueprint",
    "Metric",
    "Provenance",
    "RedTeamScenario",
    "Requirement",
    "RequirementCoverage",
    "SourceSpan",
    "TraceLink",
]
