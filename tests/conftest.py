from __future__ import annotations

from pathlib import Path

import pytest

from qa_architect.config import Settings
from qa_architect.ingestion.parser import parse_document
from qa_architect.orchestration.pipeline import build_pipeline


@pytest.fixture
def settings(tmp_path) -> Settings:
    # Force deterministic offline mode and isolate persisted data.
    return Settings(llm_provider="stub", data_dir=str(tmp_path / "data"))


@pytest.fixture
def pipeline(settings):
    return build_pipeline(settings)


@pytest.fixture
def sample_brd_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_brd.md"


@pytest.fixture
def sample_doc(sample_brd_path):
    return parse_document(str(sample_brd_path))


@pytest.fixture
def blueprint(pipeline, sample_doc):
    return pipeline.run(sample_doc, run_id="run-test")
