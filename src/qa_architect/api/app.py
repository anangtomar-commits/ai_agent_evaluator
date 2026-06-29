"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from qa_architect.config import Settings, get_settings
from qa_architect.orchestration.pipeline import build_pipeline
from qa_architect.store import RunStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="AI QA Architect",
        version="0.1.0",
        description=(
            "Upload a BRD and receive a coverage-traceable evaluation blueprint "
            "(behavioral tests + Promptfoo export). Phases 0-2."
        ),
    )

    # Shared singletons for the process lifetime.
    app.state.settings = settings
    app.state.pipeline = build_pipeline(settings)
    app.state.store = RunStore(settings.data_dir)

    from qa_architect.api.routes import router

    app.include_router(router)
    return app


app = create_app()
