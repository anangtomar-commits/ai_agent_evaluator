from pathlib import Path

from extractor.pdf_extractor import extract_text_from_pdf
from extractor.docx_extractor import extract_text_from_docx
from extractor.chunker import chunk_sections
from output_store import save_phase_output

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

_EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
}


def extract(file_path: str, original_name: str = None) -> dict:
    """
    Accepts a path to a .pdf or .docx file.
    Returns: {'filename.ext': ['chunk 1', 'chunk 2', ...]}
    Also saves the raw sections and chunks to outputs/text_extractor/.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    file_name = original_name or path.name

    # Step 1: extract sections — same interface for both file types
    sections = _EXTRACTORS[ext](file_path)

    # Step 2: chunk — applied identically regardless of source format
    sections_as_dicts = [{s["heading"]: s["text"]} for s in sections]
    chunks = chunk_sections(sections_as_dicts)

    # Step 3: persist phase-1 output (sections + chunks) for traceability
    save_phase_output(
        phase="text_extractor",
        doc_name=file_name,
        data={"document": file_name, "sections": sections, "chunks": chunks},
    )

    return {file_name: chunks}


def extract_sections(file_path: str, original_name: str = None) -> list[dict]:
    """
    Returns the raw sections list: [{'heading': ..., 'text': ...}, ...]
    Used by downstream phases that need section-level granularity.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    return _EXTRACTORS[ext](file_path)
