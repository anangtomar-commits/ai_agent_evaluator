"""FastAPI application exposing the QA Architect pipeline."""

from qa_architect.api.app import create_app

__all__ = ["create_app"]
