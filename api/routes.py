import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from extractor.extractor import extract, SUPPORTED_EXTENSIONS
from api.models import ExtractionResponse

router = APIRouter(prefix="/extract", tags=["Text Extraction"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post(
    "/",
    response_model=ExtractionResponse,
    summary="Extract text sections from a BRD document",
    description=(
        "Upload a `.pdf` or `.docx` file. "
        "Returns the document text split into sections, each with a heading and its body text."
    ),
)
async def extract_document(
    file: UploadFile = File(..., description="A .pdf or .docx BRD document"),
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
        result = extract(tmp_path)
        # Restore original filename in the response
        result["file_name"] = file.filename
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
