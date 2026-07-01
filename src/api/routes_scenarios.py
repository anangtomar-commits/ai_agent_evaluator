import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from extractor.extractor import SUPPORTED_EXTENSIONS
from scenario_generation.models import TestPlan
from scenario_generation.service import generate_from_file

router = APIRouter(prefix="/scenarios", tags=["Scenario Generator"])


@router.post(
    "/generate",
    response_model=list[TestPlan],
    summary="Generate conversational test plans for requirements extracted from a BRD",
    description=(
        "Upload a `.pdf` or `.docx` BRD document. Runs the full pipeline — text "
        "extraction → requirements extraction → strategy classification → scenario "
        "generation — and returns a TestPlan per conversational requirement. "
        "Requirements with other strategies are skipped for now."
    ),
)
async def generate_scenarios_endpoint(
    file: UploadFile = File(..., description="A .pdf or .docx BRD document"),
    model: str = Query(default="llama-3.3-70b-versatile", description="Groq model to use"),
    project_id: str = Query(..., description="ID of the project this document belongs to"),
):
    suffix = Path(file.filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        return generate_from_file(
            tmp_path, original_name=file.filename, model=model, project_id=project_id
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
