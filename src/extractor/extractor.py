from pathlib import Path

from extractor.pdf_extractor import extract_text_from_pdf
from extractor.docx_extractor import extract_text_from_docx
from extractor.chunker import chunk_sections

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

_EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
}


def extract(file_path: str, original_name: str = None) -> dict:
    """
    Accepts a path to a .pdf or .docx file.
    Returns: {'filename.ext': ['chunk 1', 'chunk 2', ...]}
    Both file types go through the same chunking pipeline after extraction.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Step 1: extract sections — same interface for both file types
    sections = _EXTRACTORS[ext](file_path)

    # Step 2: chunk — applied identically regardless of source format
    sections_as_dicts = [{s["heading"]: s["text"]} for s in sections]
    chunks = chunk_sections(sections_as_dicts)

    file_name = original_name or path.name
    return {file_name: chunks}
