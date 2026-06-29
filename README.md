# AI QA Architect

Ingests a requirements/BRD document describing an AI agent's expected behavior and
produces a **coverage-traceable evaluation blueprint**: behavioral test datasets,
(later) recommended metrics and red-team scenarios, with every artifact tagged to the
requirement ID(s) it addresses.

Implements the design in [`docs/AI_QA_Architect_Design.md`](docs/AI_QA_Architect_Design.md).

## Status — Phases 0–2

| Phase | Scope | State |
|------|-------|-------|
| 0 | Scaffolding: Blueprint IR (Pydantic v2), config, LLM provider layer, orchestrator | ✅ |
| 1 | Ingestion (md/txt/pdf/docx) + Requirement Extraction (typed, ID'd, provenance) | ✅ |
| 2 | Behavioral Test Generation (pos/neg/counter/edge) + Promptfoo export | ✅ |
| 3 | Metric Recommender + Red-Team Strategist | ⏳ planned |
| 4 | Coverage analysis + gap-driven refinement loop | ⏳ planned |
| 5 | DeepEval adapter, meta-eval, hardening | ⏳ planned |

## Architecture (this slice)

```
BRD ─► Ingestion ─► Requirement Extractor ─► Behavioral Test Generator ─► Trace Links ─► Blueprint IR ─► Promptfoo export
       (deterministic)   (LLM / stub)            (LLM / stub)           (deterministic)                  (deterministic)
```

- **Blueprint IR** (`qa_architect.ir`) is the framework-agnostic contract; export
  adapters only ever see validated IR.
- **LLM layer** (`qa_architect.llm`) is multi-provider via LiteLLM, with a deterministic
  **stub** provider so the whole pipeline runs and is fully testable offline.
- **Orchestrator** (`qa_architect.orchestration`) is a lightweight typed staged graph
  mirroring the design's node structure; documented swap path to LangGraph.

## Install

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; use source .venv/bin/activate on *nix
pip install -e ".[dev]"        # add ",llm" for real Claude, ",docs" for PDF/DOCX
```

## LLM modes

No API key → **stub mode** (deterministic, offline). To use a real model:

```bash
export ANTHROPIC_API_KEY=sk-ant-...     # LLM_PROVIDER=auto picks litellm
pip install -e ".[llm]"
```

See `.env.example` for all settings (`LLM_PROVIDER`, `LLM_MODEL`, ...).

## Usage

### CLI

```bash
python -m qa_architect.cli serve --port 8000
# qa-architect run tests/fixtures/sample_brd.md --print-promptfoo
qa-architect serve --port 8000          # FastAPI server
```

Outputs are written to `data/runs/<run_id>/` as `blueprint.json` and `promptfooconfig.yaml`.

### API

```bash
qa-architect serve            # http://127.0.0.1:8000/docs

# create a run from inline text…
curl -X POST localhost:8000/runs -F text="$(cat tests/fixtures/sample_brd.md)"
# …or from a file upload
curl -X POST localhost:8000/runs -F file=@tests/fixtures/sample_brd.md
```

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | liveness + active provider |
| POST | `/runs` | run pipeline on `file` upload or `text` field → blueprint summary |
| GET  | `/runs` | list run ids |
| GET  | `/runs/{id}` | full Evaluation Blueprint (JSON) |
| GET  | `/runs/{id}/requirements` | extracted requirements |
| GET  | `/runs/{id}/tests` | behavioral tests |
| GET  | `/runs/{id}/export/promptfoo` | promptfoo YAML (text) |

The generated `promptfooconfig.yaml` uses a placeholder `providers` entry — point it at
the agent under test before running `promptfoo eval`.

## Tests

```bash
pytest
```

28 tests cover IR validation, ingestion, requirement extraction, behavioral generation,
Promptfoo export, the end-to-end pipeline, and every API endpoint — all in stub mode (no
network/key required).
