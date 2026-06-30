from collections import Counter

from scenario_generation.models import Scenario


class ScenarioValidationError(Exception):
    """Raised when a generated set of scenarios fails validation."""


def validate_scenarios(
    scenarios: list[Scenario],
    requirement_id: str,
    distribution: dict[str, int],
) -> list[str]:
    """
    Checks a generated scenario set against the rules defined in the plan.

    Returns a list of human-readable error messages. An empty list means the
    scenarios are valid.
    """
    errors: list[str] = []

    # IDs are unique.
    ids = [s.id for s in scenarios]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate scenario IDs found.")

    # Scenario types match the requested distribution.
    type_counts = Counter(s.scenario_type for s in scenarios)
    for scenario_type, expected in distribution.items():
        actual = type_counts.get(scenario_type, 0)
        if actual != expected:
            errors.append(
                f"Expected {expected} '{scenario_type}' scenarios, got {actual}."
            )
    # No unexpected types beyond the distribution.
    for scenario_type in type_counts:
        if scenario_type not in distribution:
            errors.append(f"Unexpected scenario type '{scenario_type}'.")

    # No duplicate titles.
    titles = [s.title.strip().lower() for s in scenarios]
    if len(titles) != len(set(titles)):
        errors.append("Duplicate scenario titles found.")

    # No duplicate descriptions.
    descriptions = [s.description.strip().lower() for s in scenarios]
    if len(descriptions) != len(set(descriptions)):
        errors.append("Duplicate scenario descriptions found.")

    # Every scenario has an objective and references the correct requirement.
    for s in scenarios:
        if not s.objective.strip():
            errors.append(f"Scenario '{s.id}' is missing an objective.")
        if s.requirement_id != requirement_id:
            errors.append(
                f"Scenario '{s.id}' references '{s.requirement_id}', "
                f"expected '{requirement_id}'."
            )

    return errors
