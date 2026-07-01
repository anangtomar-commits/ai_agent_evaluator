import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, UploadFile, File, Query

from db import pipeline_runs
from extractor.extractor import extract, SUPPORTED_EXTENSIONS
from api.models import ExtractionResponse

router = APIRouter(prefix="/extract", tags=["Text Extraction"])


@router.post(
    "/",
    response_model=ExtractionResponse,
    summary="Extract text chunks from a BRD document",
    description=(
        "Upload a `.pdf` or `.docx` file. "
        "Returns document text as token-bounded chunks (~6 000 tokens each, 600-token overlap)."
    ),
)
async def extract_document(
    response: Response,
    file: UploadFile = File(..., description="A .pdf or .docx BRD document"),
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
        result = extract(tmp_path, original_name=file.filename, project_id=project_id, run_id=run_id)
        pipeline_runs.mark_status(run_id, "COMPLETED")
        response.headers["X-Run-Id"] = run_id
        return result
    except Exception as exc:
        pipeline_runs.mark_status(run_id, "FAILED")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
