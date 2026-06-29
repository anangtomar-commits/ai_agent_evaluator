"""Controlled vocabularies for the Blueprint IR."""

from __future__ import annotations

from enum import Enum


class RequirementType(str, Enum):
    GOAL = "goal"
    TONE = "tone"
    BUSINESS_RULE = "business_rule"
    GUARDRAIL = "guardrail"
    COMPLIANCE = "compliance"
    SUCCESS_CRITERION = "success_criterion"
    DOMAIN_CONTEXT = "domain_context"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestCategory(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    COUNTER_EXAMPLE = "counter_example"
    EDGE_CASE = "edge_case"


class AssertionKind(str, Enum):
    LLM_RUBRIC = "llm_rubric"
    REGEX = "regex"
    EQUALS = "equals"
    CONTAINS = "contains"
    METRIC_REF = "metric_ref"


class MetricLevel(str, Enum):
    AGENT = "agent"
    BUSINESS_KPI = "business_kpi"


class MeasurementMethod(str, Enum):
    LLM_JUDGE = "llm_judge"
    RULE = "rule"
    STATISTICAL = "statistical"
    HUMAN = "human"


class AttackClass(str, Enum):
    JAILBREAK = "jailbreak"
    PROMPT_INJECTION = "prompt_injection"
    MISUSE = "misuse"
    POLICY_VIOLATION = "policy_violation"
    DATA_EXFIL = "data_exfil"


class CoverageDimension(str, Enum):
    TESTED = "tested"
    MEASURED = "measured"
    ADVERSARIALLY_PROBED = "adversarially_probed"


class VerifiedBy(str, Enum):
    SELF_TAG = "self_tag"
    SEMANTIC = "semantic"
