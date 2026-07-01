from typing import Literal

from pydantic import BaseModel

from requirements_extractor.models import Requirement


class Scenario(BaseModel):
    id: str
    """System-assigned scenario ID, unique within a TestPlan, e.g. REQ-000003-SCN-001."""

    requirement_id: str
    """ID of the Requirement this scenario was generated from."""

    scenario_type: Literal["Positive", "Negative", "Boundary", "Adversarial"]
    """The category of user interaction this scenario exercises."""

    title: str
    """Short, human-readable name for the scenario."""

    objective: str
    """What this scenario is trying to verify."""

    description: str
    """Concrete description of the situation that should be tested."""

    preconditions: list[str]
    """State / setup that must hold before the scenario runs."""

    user_goal: str
    """What the end user is trying to achieve in this interaction."""

    risk_area: str
    """The risk this scenario guards against (e.g. wrong language, data leak)."""

    priority: str
    """High | Medium | Low — relative importance of this scenario."""


class TestPlan(BaseModel):
    requirement_id: str
    """ID of the Requirement this test plan covers."""

    requirement: Requirement
    """The full requirement (statement, type, domain, priority, …) this plan was built from."""

    strategy: str
    """Test strategy used to generate the scenarios, e.g. Conversational."""

    rationale: str
    """Brief explanation of why these scenarios were generated."""

    scenarios: list[Scenario]
    """The generated scenarios for this requirement."""
