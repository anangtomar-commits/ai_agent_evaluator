from pydantic import BaseModel


class Requirement(BaseModel):
    # ── Identity ──────────────────────────────────────────────────────────────
    id: str
    """Globally unique system-assigned ID, e.g. REQ-000001."""

    source_requirement: str | None = None
    """Requirement ID exactly as it appears in the BRD (e.g. FR-A01, G-01). None if absent."""

    # ── Classification ───────────────────────────────────────────────────────
    type: str
    """
    RequirementType — what kind of requirement this is:
      Functional | NonFunctional | BusinessRule | Constraint | Assumption | Goal | Risk | AcceptanceCriteria
    """

    domain: str
    """
    RequirementDomain — which system area this requirement belongs to:
      API | Security | Performance | Language | Logging | Deployment |
      UI | DataManagement | Integration | Authentication | Notification | ErrorHandling
    """

    # ── Content ───────────────────────────────────────────────────────────────
    statement: str
    """Clean, normalised, atomic requirement statement."""

    priority: str
    """High | Medium | Low — inferred from modal language (must/shall → High, should → Medium, may/could → Low)."""

    # ── Testability ───────────────────────────────────────────────────────────
    testable: bool
    """True when the requirement can be validated by a QA tester without access to internals."""

    acceptance_criteria: str
    """One concrete, measurable pass/fail condition — fed directly into deepeval / promptfoo assertions."""

    ambiguity_flag: bool
    """True when the statement uses unmeasurable language and needs human review before test generation."""

    tags: list[str]
    """Lowercase kebab-case labels for test-suite filtering, e.g. ["functional", "high-priority", "language"]."""

    # ── Source traceability ───────────────────────────────────────────────────
    source_text: str | None = None
    """Verbatim BRD excerpt (≤ 200 chars) this requirement was drawn from."""

    source_section: str | None = None
    """Section identifier where this requirement was found, e.g. "5.2"."""

    source_page: int | None = None
    """Document page on which this requirement appears."""



class SectionRequirements(BaseModel):
    section_id: str | None = None
    """Numeric or alphanumeric section identifier parsed from the heading, e.g. "5.2"."""

    section_title: str
    """Human-readable section title, e.g. "Answer Mode"."""

    page_start: int | None = None
    """Document page on which this section begins."""

    page_end: int | None = None
    """Document page on which this section ends."""

    requirements: list[Requirement]
