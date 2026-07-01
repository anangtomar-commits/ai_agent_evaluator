import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from extractor.extractor import SUPPORTED_EXTENSIONS
from requirements_extractor.extractor import extract_requirements
from requirements_extractor.models import SectionRequirements

router = APIRouter(prefix="/requirements", tags=["Requirements Extraction"])


@router.post(
    "/extract",
    response_model=list[SectionRequirements],
    summary="Extract structured requirements from a BRD document",
    description=(
        "Upload a `.pdf` or `.docx` BRD document. "
        "Returns a list of sections, each containing structured requirements with metadata "
        "fields designed for use with promptfoo and deepeval."
    ),
)
async def extract_requirements_endpoint(
    file: UploadFile = File(..., description="A .pdf or .docx BRD document"),
    model: str = Query(default="llama-3.3-70b-versatile", description="Groq model to use for extraction"),
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
        results = extract_requirements(
            tmp_path, original_name=file.filename, model=model, project_id=project_id
        )
        return results
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
