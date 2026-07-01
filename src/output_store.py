import json
from datetime import datetime
from pathlib import Path

_OUTPUT_ROOT = Path(__file__).parent.parent / "outputs"


def save_phase_output(
    phase: str,
    doc_name: str,
    data: dict | list,
    project_id: str = None,
) -> Path:
    """
    Saves `data` as a timestamped JSON file under outputs/<phase>/.
    Wraps it with project_id/phase/document metadata so the file can later be
    loaded straight into a Postgres row without re-deriving that context.
    Returns the path of the written file.
    """
    folder = _OUTPUT_ROOT / phase
    folder.mkdir(parents=True, exist_ok=True)

    stem = Path(doc_name).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = folder / f"{stem}_{timestamp}.json"

    envelope = {
        "project_id": project_id,
        "phase": phase,
        "document": doc_name,
        "generated_at": datetime.now().isoformat(),
        "data": data,
    }

    out_path.write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path
