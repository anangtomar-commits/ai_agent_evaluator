from openai import OpenAI

from requirements_extractor.models import Requirement
from scenario_generation.generators.base_generator import BaseScenarioGenerator
from scenario_generation.generators.conversational_generator import (
    ConversationScenarioGenerator,
)
from scenario_generation.models import TestPlan

# ── Strategy registry ────────────────────────────────────────────────────────
# Maps a requirement's test_strategy to the generator that handles it.
# To support a new strategy later, implement a BaseScenarioGenerator and add one
# line here — the planner and service never change.
#
#   "Performance":    PerformanceScenarioGenerator,
#   "Security":       SecurityScenarioGenerator,
#   "Infrastructure": InfrastructureScenarioGenerator,
#   "BusinessKPI":    BusinessKPIScenarioGenerator,
_GENERATOR_REGISTRY: dict[str, type[BaseScenarioGenerator]] = {
    "Conversational": ConversationScenarioGenerator,
}


class ScenarioPlanner:
    """
    Routes a requirement to the correct strategy generator.

    The planner has no knowledge of how any strategy builds its scenarios — it
    only looks up the registered generator and delegates to it.
    """

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def plan(self, requirement: Requirement) -> TestPlan | type[NotImplemented]:
        """
        Returns a TestPlan for the requirement, or NotImplemented when no
        generator is registered for its strategy (e.g. Performance, Security).
        """
        generator_cls = _GENERATOR_REGISTRY.get(requirement.test_strategy)
        if generator_cls is None:
            return NotImplemented

        generator = generator_cls(self.client, self.model)
        return generator.generate(requirement)
