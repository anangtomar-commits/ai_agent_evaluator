"""HTTP routes for the QA Architect pipeline."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse

from qa_architect.export.promptfoo import to_promptfoo_yaml
from qa_architect.ingestion.parser import parse_bytes, parse_text
from qa_architect.ir import EvaluationBlueprint
from qa_architect.orchestration.pipeline import Pipeline
from qa_architect.store import RunStore

router = APIRouter()


def _pipeline(request: Request) -> Pipeline:
    return request.app.state.pipeline


def _store(request: Request) -> RunStore:
    return request.app.state.store


def _get_or_404(request: Request, run_id: str) -> EvaluationBlueprint:
    blueprint = _store(request).get(run_id)
    if blueprint is None:
        raise HTTPException(status_code=404, detail=f"run '{run_id}' not found")
    return blueprint


def _summary(blueprint: EvaluationBlueprint) -> dict:
    return {
        "run_id": blueprint.generation_run_id,
        "version": blueprint.version,
        "document": blueprint.doc_metadata.model_dump(),
        "counts": {
            "requirements": len(blueprint.requirements),
            "tests": len(blueprint.tests),
            "metrics": len(blueprint.metrics),
            "red_team": len(blueprint.red_team),
            "trace_links": len(blueprint.trace_links),
        },
        "provider": blueprint.provenance.llm_provider,
        "links": {
            "self": f"/runs/{blueprint.generation_run_id}",
            "requirements": f"/runs/{blueprint.generation_run_id}/requirements",
            "tests": f"/runs/{blueprint.generation_run_id}/tests",
            "promptfoo": f"/runs/{blueprint.generation_run_id}/export/promptfoo",
        },
    }


@router.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "provider": _pipeline(request).llm.provider_name}


@router.post("/runs")
async def create_run(
    request: Request,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    name: str | None = Form(default=None),
) -> dict:
    """Create a run from an uploaded BRD file OR inline markdown/plaintext."""
    if file is not None:
        data = await file.read()
        document = parse_bytes(data, name=file.filename or name or "upload")
    elif text:
        document = parse_text(text, name=name or "inline.md")
    else:
        raise HTTPException(
            status_code=400, detail="Provide either a 'file' upload or 'text' field."
        )

    blueprint = _pipeline(request).run(document)
    _store(request).save(blueprint)
    return _summary(blueprint)


@router.get("/runs")
def list_runs(request: Request) -> dict:
    return {"runs": _store(request).list_ids()}


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str) -> EvaluationBlueprint:
    return _get_or_404(request, run_id)


@router.get("/runs/{run_id}/requirements")
def get_requirements(request: Request, run_id: str) -> dict:
    blueprint = _get_or_404(request, run_id)
    return {"requirements": [r.model_dump() for r in blueprint.requirements]}


@router.get("/runs/{run_id}/tests")
def get_tests(request: Request, run_id: str) -> dict:
    blueprint = _get_or_404(request, run_id)
    return {"tests": [t.model_dump() for t in blueprint.tests]}


@router.get("/runs/{run_id}/export/promptfoo", response_class=PlainTextResponse)
def export_promptfoo(request: Request, run_id: str) -> str:
    blueprint = _get_or_404(request, run_id)
    return to_promptfoo_yaml(blueprint)
