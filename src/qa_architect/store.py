"""Simple run store: in-memory index + on-disk JSON/YAML persistence.

POC-grade (single process). The scale path swaps this for SQLite/Postgres + blob
storage behind the same interface.
"""

from __future__ import annotations

from pathlib import Path

from qa_architect.export.promptfoo import to_promptfoo_yaml
from qa_architect.ir import EvaluationBlueprint


class RunStore:
    def __init__(self, data_dir: str = "data") -> None:
        self.root = Path(data_dir) / "runs"
        self._cache: dict[str, EvaluationBlueprint] = {}

    def _run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def save(self, blueprint: EvaluationBlueprint) -> None:
        self._cache[blueprint.generation_run_id] = blueprint
        run_dir = self._run_dir(blueprint.generation_run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "blueprint.json").write_text(
            blueprint.model_dump_json(indent=2), encoding="utf-8"
        )
        (run_dir / "promptfooconfig.yaml").write_text(
            to_promptfoo_yaml(blueprint), encoding="utf-8"
        )

    def get(self, run_id: str) -> EvaluationBlueprint | None:
        if run_id in self._cache:
            return self._cache[run_id]
        path = self._run_dir(run_id) / "blueprint.json"
        if path.exists():
            blueprint = EvaluationBlueprint.model_validate_json(
                path.read_text(encoding="utf-8")
            )
            self._cache[run_id] = blueprint
            return blueprint
        return None

    def list_ids(self) -> list[str]:
        ids = set(self._cache)
        if self.root.exists():
            ids.update(p.name for p in self.root.iterdir() if p.is_dir())
        return sorted(ids)
