from abc import ABC, abstractmethod

from openai import OpenAI

from requirements_extractor.models import Requirement
from scenario_generation.models import TestPlan


class BaseScenarioGenerator(ABC):
    """
    Contract for every strategy-specific scenario generator.

    Concrete generators (Conversational, Performance, Security, …) implement
    `generate` and are registered with the ScenarioPlanner. The orchestration
    layer only ever talks to this interface — it never knows how a particular
    strategy builds its scenarios.
    """

    #: The test_strategy value this generator handles, e.g. "Conversational".
    strategy: str

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    @abstractmethod
    def generate(self, requirement: Requirement) -> TestPlan:
        """Produce a validated TestPlan for a single requirement."""
        raise NotImplementedError
