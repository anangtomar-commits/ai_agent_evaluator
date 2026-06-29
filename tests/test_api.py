"""API endpoint tests via Starlette TestClient (stub mode)."""

import pytest
import yaml
from fastapi.testclient import TestClient

from qa_architect.api.app import create_app
from qa_architect.config import Settings


@pytest.fixture
def client(tmp_path):
    settings = Settings(llm_provider="stub", data_dir=str(tmp_path / "data"))
    return TestClient(create_app(settings))


def _create_from_text(client, sample_brd_path):
    brd = sample_brd_path.read_text(encoding="utf-8")
    resp = client.post("/runs", data={"text": brd, "name": "sample_brd.md"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["provider"] == "stub"


def test_create_run_from_text(client, sample_brd_path):
    summary = _create_from_text(client, sample_brd_path)
    assert summary["counts"]["requirements"] >= 8
    assert summary["counts"]["tests"] > 0
    assert summary["provider"] == "stub"


def test_create_run_from_file_upload(client, sample_brd_path):
    with sample_brd_path.open("rb") as fh:
        resp = client.post(
            "/runs",
            files={"file": ("sample_brd.md", fh, "text/markdown")},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["counts"]["tests"] > 0


def test_create_run_requires_input(client):
    resp = client.post("/runs")
    assert resp.status_code == 400


def test_full_run_lifecycle(client, sample_brd_path):
    summary = _create_from_text(client, sample_brd_path)
    run_id = summary["run_id"]

    assert run_id in client.get("/runs").json()["runs"]

    reqs = client.get(f"/runs/{run_id}/requirements").json()["requirements"]
    assert len(reqs) >= 8

    tests = client.get(f"/runs/{run_id}/tests").json()["tests"]
    assert tests

    export = client.get(f"/runs/{run_id}/export/promptfoo")
    assert export.status_code == 200
    config = yaml.safe_load(export.text)
    assert len(config["tests"]) == len(tests)


def test_missing_run_returns_404(client):
    assert client.get("/runs/nope").status_code == 404
