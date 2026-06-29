# AI QA Architect — System Design Blueprint

## Context

We are building an **agentic AI system ("AI QA Architect")** that ingests a requirements/BRD
document describing the expected behavior of an *AI agent* and automatically produces a
**comprehensive evaluation blueprint**: behavioral test datasets, recommended metrics & KPIs,
business-aware red-team scenarios, and a coverage analysis that proves every requirement is
exercised.

This is a **POC first** — infra stays simple, but the architecture must decompose cleanly into a
scalable service later. Stack is **Python**, agents run on a **multi-provider** LLM abstraction
(default to latest Claude — Opus 4.8 / Sonnet 4.6 — swappable to OpenAI/others via config).

The central design principle is **requirement-centric traceability**: every generated artifact
(test, metric, red-team scenario) is tagged with the requirement ID(s) it addresses, so coverage is
*computed and provable*, not guessed.

---

## 1. High-Level Architecture

A **staged pipeline of specialized agents** orchestrated as a stateful graph, all operating on one
evolving aggregate artifact — the **Evaluation Blueprint** (a framework-agnostic Intermediate
Representation, "IR").

```
                         ┌─────────────────────────────────────────────┐
   BRD (pdf/docx/md) ──► │ 1. Ingestion & Parsing  (deterministic)      │
                         └───────────────┬─────────────────────────────┘
                                         ▼
                         ┌─────────────────────────────────────────────┐
                         │ 2. Requirement Extraction (LLM, structured)  │  ◄── stable Requirement IDs
                         └───────────────┬─────────────────────────────┘
                                         ▼
                         ┌─────────────────────────────────────────────┐
                         │ 3. Domain & Risk Enrichment (RAG + classify) │  ◄── domain packs, risk taxonomy
                         └───────────────┬─────────────────────────────┘
                                         ▼
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
   ┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐
   │ 4a. Behavioral     │   │ 4b. Metric         │   │ 4c. Red-Team       │   (parallel fan-out)
   │     Test Generator │   │     Recommender    │   │     Strategist     │
   └─────────┬──────────┘   └─────────┬──────────┘   └─────────┬──────────┘
             └──────────────┬─────────┴────────────────────────┘
                            ▼
              ┌─────────────────────────────────────────────┐
              │ 5. Critic / Validator (dedup, schema, QA)    │
              └───────────────┬─────────────────────────────┘
                              ▼
              ┌─────────────────────────────────────────────┐
              │ 6. Coverage Analyst  ── gap? ──► targeted    │  ◄── refinement loop
              │    re-generation (back to 4x)                │      (until threshold / max iters)
              └───────────────┬─────────────────────────────┘
                              ▼
              ┌─────────────────────────────────────────────┐
              │ 7. Compiler & Export Adapters                │ ──► Promptfoo YAML (1st)
              │    (Blueprint IR → framework files)          │ ──► DeepEval (2nd), JSON
              └───────────────┬─────────────────────────────┘
                              ▼
              ┌─────────────────────────────────────────────┐
              │ 8. Human Review / Approve / Refine (HITL)    │
              └─────────────────────────────────────────────┘
```

**Why a pipeline + shared aggregate (not a free-form multi-agent swarm):** the problem is
naturally a DAG with one critique/refine loop. A staged graph gives determinism, debuggability,
resumability, and cost control — all essential for a tool whose *job* is rigor. The only true
agentic loop is **coverage-driven re-generation** (step 6 → 4x).

---

## 2. Agent Architecture & Responsibilities

| # | Agent | Type | Responsibility | Key output |
|---|-------|------|----------------|-----------|
| 1 | **Ingestion** | Deterministic | Parse pdf/docx/md, normalize, section-chunk, preserve provenance (page/section offsets) | Normalized document tree |
| 2 | **Requirement Extractor** | LLM (structured output) | Extract *atomic* requirements; classify each (goal / tone / business-rule / guardrail / compliance / success-criterion / domain-context); assign stable IDs; capture source span | `Requirement[]` |
| 3 | **Domain & Risk Enrichment** | LLM + RAG | Retrieve domain knowledge pack; map requirements to a risk taxonomy (OWASP LLM Top 10, MITRE ATLAS, domain rules); flag compliance regimes | Enriched requirements + risk tags |
| 4a | **Behavioral Test Generator** | LLM | Per requirement → positive examples, negative examples, counter-examples, edge cases; each tagged with requirement IDs + expected assertion | `BehavioralTest[]` |
| 4b | **Metric Recommender** | LLM + Metric Catalog | Recommend agent-level metrics (accuracy, tone adherence, hallucination rate, safety…) + business KPIs; specify *how to measure* and *data required* | `Metric[]` |
| 4c | **Red-Team Strategist** | LLM + Risk taxonomy | Generate adversarial scenarios (jailbreaks, prompt injections, misuse, policy violations) from risks; **prioritize by business impact × likelihood** | `RedTeamScenario[]` |
| 5 | **Critic / Validator** | LLM-judge + rules | Schema validation, semantic dedup, relevance check, hallucination guard on generated artifacts; quality gate before coverage | Validated/flagged artifacts |
| 6 | **Coverage Analyst** | LLM + deterministic | Build traceability matrix (requirement → artifacts), compute coverage scores per dimension, list gaps, decide refine-vs-stop | `CoverageReport` + refine signal |
| 7 | **Compiler / Exporter** | Deterministic | Assemble Blueprint IR; render framework adapters | Promptfoo YAML / DeepEval / JSON |
| — | **Orchestrator** | Graph (LangGraph) | State machine, parallel fan-out, retry, checkpoint, loop control | — |

Design notes:
- **LLM agents emit typed structured output** (Pydantic-validated) — no free-text parsing.
- **Generators self-tag** the requirement IDs they cover (primary coverage signal); the Coverage
  Analyst additionally does semantic verification (catches mis-tagging / over-claiming).
- **Critic is separate from generators** to avoid self-grading bias.
- Ingestion & Compiler are **deterministic** (cheap, reliable) — keep LLMs out where not needed.

---

## 3. Data Models & Schemas (Pydantic v2)

Conceptual shapes (field-level, not final code):

- **`Requirement`** — `id`, `type` (enum), `statement`, `rationale`, `source_span`
  (doc/page/section), `priority`, `domain_tags[]`, `risk_tags[]`, `acceptance_criteria[]`,
  `ambiguity_flag`.
- **`BehavioralTest`** — `id`, `requirement_ids[]`, `category` (positive | negative |
  counter_example | edge_case), `input` (user/turn or conversation), `expected_behavior`,
  `assertion` (judge rubric / regex / equality / metric ref), `rationale`.
- **`Metric`** — `id`, `requirement_ids[]`, `level` (agent | business_kpi), `name`,
  `definition`, `measurement_method` (LLM-judge | rule | statistical | human),
  `data_required`, `target_threshold`, `framework_hint` (deepeval g-eval, promptfoo assert…).
- **`RedTeamScenario`** — `id`, `requirement_ids[]`, `attack_class` (jailbreak |
  prompt_injection | misuse | policy_violation | data_exfil…), `technique`, `attack_prompt`,
  `expected_safe_behavior`, `severity`, `likelihood`, `business_impact`, `priority_score`.
- **`TraceLink`** — `requirement_id`, `artifact_id`, `artifact_type`, `coverage_dimension`
  (tested | measured | adversarially_probed), `confidence`, `verified_by` (self_tag | semantic).
- **`CoverageReport`** — per-requirement coverage across 3 dimensions, aggregate scores, `gaps[]`,
  `uncovered_requirement_ids[]`, `recommendations[]`.
- **`EvaluationBlueprint`** (root aggregate) — `doc_metadata`, `requirements[]`, `tests[]`,
  `metrics[]`, `red_team[]`, `coverage`, `provenance`, `version`, `generation_run_id`.

The **Blueprint IR is the contract** between generation and export. Adapters never see raw LLM
output — only the validated IR.

---

## 4. End-to-End Workflow

1. **Upload BRD** → Ingestion parses & normalizes, retains source provenance.
2. **Extract requirements** → typed, ID'd, span-linked. *(Optional HITL checkpoint: user confirms/edits
   the requirement list — highest-leverage human review point.)*
3. **Enrich** with domain knowledge + risk taxonomy mapping.
4. **Fan-out generation** (parallel): behavioral tests, metrics, red-team scenarios — each tagging
   requirement IDs.
5. **Critic** validates schema, dedups, checks relevance/hallucination; flags weak artifacts.
6. **Coverage analysis** builds the traceability matrix and scores each requirement on
   {tested, measured, adversarially_probed}. If gaps exceed threshold → **targeted re-generation**
   for only the uncovered/under-covered requirements (bounded by max iterations & budget).
7. **Compile** Blueprint IR → **Promptfoo** suite first; **DeepEval** + JSON exports next.
8. **Human review/approve**; approved blueprint is versioned and stored. Re-runs are diffable.
9. *(Downstream, out of POC scope)* the exported suites run against the *actual* agent under test in
   CI; results can feed back as evidence.

---

## 5. Knowledge Representation Strategy

- **Requirement graph** — atomic requirements as nodes with relationships (refines, conflicts-with,
  depends-on). Backbone of traceability.
- **Risk taxonomy** — curated, versioned mapping: OWASP LLM Top 10 + MITRE ATLAS + domain-specific
  policy catalogs (e.g., finance: fair-lending, PII; healthcare: PHI/HIPAA). Drives red-teaming and
  compliance coverage.
- **Metric catalog** — reusable library of known metrics with canonical `measurement_method` and
  `data_required`, so the Metric Recommender *selects & adapts* rather than inventing from scratch
  (reduces hallucination, improves consistency).
- **Domain knowledge packs** — RAG corpora (regulations, domain glossaries, prior blueprints) in a
  vector store; retrieved during enrichment & generation.
- **Traceability matrix** — the live graph linking requirements ↔ artifacts ↔ coverage dimensions;
  the single source for coverage scoring and gap detection.

Representation is **hybrid**: curated taxonomies/catalogs (precision, governance) + RAG packs
(breadth, freshness) + LLM reasoning (synthesis). POC can store graphs as JSON/SQLite rows; promote
to a graph/relational store at scale.

---

## 6. Coverage Methodology

**Three coverage dimensions per requirement:**
1. **Tested** — ≥1 behavioral test (with positive *and* negative/edge variety where applicable).
2. **Measured** — ≥1 metric quantifies adherence.
3. **Adversarially probed** — ≥1 red-team scenario for requirements carrying risk/guardrail/compliance tags.

**Scoring:**
- Generators **self-tag** requirement IDs (primary signal).
- Coverage Analyst **verifies semantically** (embeddings + LLM-judge) to catch mis-tags and
  over-claiming; mismatches lower `confidence` and can force regeneration.
- Per-requirement coverage = weighted function of the three dimensions, scaled by requirement
  `priority`. Aggregate dashboard + explicit **gap list** of uncovered/under-covered IDs.
- **Refinement loop**: gaps trigger *targeted* re-generation (only the deficient requirements),
  bounded by max iterations and token budget, until threshold met or budget exhausted.
- **Rubric-based quality**, not just counts: e.g., a guardrail requirement with only positive tests
  is flagged under-covered even if "tested" is technically true.

---

## 7. Recommended Tech Stack

| Concern | Choice (POC) | Scale path |
|---|---|---|
| Language/runtime | **Python 3.11+** | same |
| Orchestration | **LangGraph** (stateful graph, checkpointing, loops, parallel fan-out) | same, + durable checkpointer |
| LLM provider abstraction | **LiteLLM** (multi-provider; default Claude Opus 4.8 / Sonnet 4.6, swap via config) | + provider routing/fallback |
| Structured output | Pydantic v2 + native tool/JSON-schema outputs (Instructor optional) | same |
| Doc parsing | `pymupdf` / `python-docx` / `markdown` (consider `docling`/`unstructured`) | service + OCR |
| Vector store | **Chroma / LanceDB** (local/embedded) | **pgvector** / managed |
| Persistence | **SQLite** + Blueprint JSON files | **Postgres** |
| API | **FastAPI** | same + queue (Celery/Arq) for long runs |
| UI | **Streamlit** (review/approve) | React/Next.js |
| Observability | **Langfuse** (LLM tracing, cost, latency) | same |
| Eval export #1 | **Promptfoo** (declarative YAML, CI-native, **red-team plugins**) | same |
| Eval export #2 | **DeepEval** (rich runtime metrics: G-Eval, hallucination, faithfulness) | same |
| Meta-eval | Use Promptfoo/DeepEval to evaluate *our own* outputs (golden BRDs) | regression gate in CI |

---

## 8. Build vs Buy Analysis

**BUY (integrate):**
- **LangGraph** — orchestration/state/loops. Reinventing a stateful agent graph is wasted effort.
- **LiteLLM** — multi-provider abstraction (your requirement) for ~free.
- **Promptfoo** — *export + execution target* and the **red-team engine**. Its adversarial plugin
  catalog (jailbreaks, injections) is mature; we *feed* it domain-specific scenarios rather than
  rebuilding attack generation. **→ first adapter.**
- **DeepEval** — *export + execution target* for metric-rich runtime scoring (G-Eval etc.).
  **→ second adapter.**
- **OpenAI Evals** — **SKIP.** OpenAI-centric, less flexible, conflicts with multi-provider goal.
  Revisit only if a customer standardizes on it.

**BUILD (our differentiated IP):**
- Requirement extraction + classification + provenance.
- **Evaluation Blueprint IR** (framework-agnostic source of truth).
- Domain/risk enrichment + risk taxonomy & metric catalog curation.
- **Coverage engine** (traceability matrix, scoring, gap-driven refinement) — *the core moat*.
- Generators' domain logic + Critic.
- Export adapters (IR → Promptfoo/DeepEval/JSON).

**Verdict:** buy orchestration/provider/execution-frameworks; build the *intelligence* (extraction,
IR, coverage, generation strategy). This keeps the POC small while owning the defensible part.
The framework-agnostic IR means switching/adding eval frameworks is an adapter change, not a rewrite.

---

## 9. MVP Roadmap

- **Phase 0 — Scaffolding:** repo, Pydantic schemas (IR), LiteLLM provider layer, LangGraph skeleton,
  config, Langfuse tracing. *Exit: empty graph runs end-to-end with stubbed nodes.*
- **Phase 1 — Ingestion + Requirement Extraction (+ HITL review):** parse BRD → typed `Requirement[]`
  with provenance; Streamlit screen to confirm/edit. *Exit: accurate requirement list from a real BRD.*
- **Phase 2 — Behavioral Test Generation + Promptfoo export:** positive/negative/counter/edge per
  requirement → IR → runnable Promptfoo YAML. *Exit: a real Promptfoo suite generated from a BRD.*
- **Phase 3 — Metric Discovery + Red-Team Strategist:** metric catalog + KPI recommendations; risk
  taxonomy → prioritized adversarial scenarios → Promptfoo red-team config. *Exit: all 3 pillars produce artifacts.*
- **Phase 4 — Coverage Analysis + refinement loop:** traceability matrix, scoring, gap detection,
  targeted re-generation. *Exit: coverage report + provable closure of gaps. **This is the demo centerpiece.***
- **Phase 5 — Hardening:** DeepEval adapter, meta-eval on golden BRDs, cost/latency budgets, error
  handling, export polish, docs. *Exit: POC review-ready and scalable in principle.*

Demo narrative: *upload a BRD → get a coverage-complete evaluation blueprint with runnable Promptfoo
suites and a traceability matrix proving every requirement is tested, measured, and probed.*

---

## 10. Risks, Assumptions & Open Questions

**Risks**
- **BRD ambiguity/variance** — vague requirements yield weak tests. Mitigate: ambiguity flagging +
  HITL confirmation at Phase 1.
- **Hallucinated/irrelevant artifacts** — Mitigate: Critic agent, self-tag + semantic verification,
  human approval gate.
- **Coverage validity** — "covered" must mean *meaningfully* covered, not count-gaming. Mitigate:
  rubric-based scoring, dimension weighting, meta-eval.
- **No ground truth for "good blueprint"** — meta-eval is itself fuzzy. Mitigate: curated golden
  BRD→blueprint pairs + expert spot-review.
- **Cost/latency** of multi-agent fan-out + refine loops. Mitigate: budget caps, model tiering
  (cheap model for extraction/critic, strong model for generation), caching.
- **Compliance domains** require expert validation; system *assists*, does not certify.
- **Prompt-injection via the BRD itself** (untrusted input) — treat document content as data, not
  instructions; sandbox.

**Assumptions**
- BRDs are text-extractable (not pure scanned images) for POC.
- Single-tenant POC; no auth/RBAC/billing yet (architected to add later).
- The *agent under test* is out of scope — we produce the blueprint, not run it against a live agent
  in the POC.
- Multi-provider with Claude as default is acceptable for the POC.

**Open questions**
1. Are target BRDs a consistent template, or free-form across teams? (affects extraction prompting)
2. Which **domains** must the POC demo first (finance / healthcare / general support)? — drives which
   risk taxonomy & domain pack we curate first.
3. Is downstream execution (running suites against a real agent) in scope for the POC demo, or just
   blueprint generation?
4. Acceptable **cost/latency** envelope per BRD run?
5. Compliance posture — do generated compliance artifacts need expert sign-off in-product?
6. Output delivery — files/repo PR, downloadable bundle, or hosted dashboard?

---

## Verification (how we'll validate the build, when implemented)

- **Golden-set meta-eval:** maintain 2–3 representative BRDs with hand-reviewed "expected" blueprints;
  run the pipeline and score requirement-extraction recall, artifact relevance, and coverage closure.
- **Export validity:** generated **Promptfoo YAML must execute** (`promptfoo eval` runs without schema
  errors against a stub agent); DeepEval files import & run.
- **Coverage correctness:** unit tests on the coverage engine with synthetic requirement/artifact sets
  (known gaps must be detected; full coverage must report closed).
- **Traceability integrity:** every artifact links to ≥1 valid requirement ID; no orphan IDs.
- **Tracing/cost:** Langfuse confirms per-run token/cost within budget; refinement loop terminates.
- **HITL flow:** edit a requirement in review → downstream artifacts regenerate consistently.

---

*Status: design deliverable for review. No application code is to be written until this design is approved.*
