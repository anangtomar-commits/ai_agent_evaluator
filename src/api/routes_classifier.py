import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, UploadFile, File, Query

from db import pipeline_runs
from extractor.extractor import SUPPORTED_EXTENSIONS
from requirements_extractor.models import SectionRequirements
from test_strategy_classifier.classifier import classify_from_file

router = APIRouter(prefix="/classify", tags=["Test Strategy Classifier"])


@router.post(
    "/strategies",
    response_model=list[SectionRequirements],
    summary="Classify test strategies for requirements extracted from a BRD document",
    description=(
        "Upload a `.pdf` or `.docx` BRD document. "
        "Runs the full pipeline — text extraction → requirements extraction → "
        "test strategy classification — and returns requirements annotated with "
        "`test_strategy`: Conversational | Performance | Security | BusinessKPI | Infrastructure."
    ),
)
async def classify_strategies_endpoint(
    response: Response,
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

    run_id = str(uuid.uuid4())
    try:
        results = classify_from_file(
            tmp_path, original_name=file.filename, model=model, project_id=project_id, run_id=run_id
        )
        pipeline_runs.mark_status(run_id, "COMPLETED")
        response.headers["X-Run-Id"] = run_id
        return results
    except EnvironmentError as exc:
        pipeline_runs.mark_status(run_id, "FAILED")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        pipeline_runs.mark_status(run_id, "FAILED")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
