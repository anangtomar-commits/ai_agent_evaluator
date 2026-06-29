import os
from pathlib import Path

from extractor.pdf_extractor import extract_text_from_pdf
from extractor.docx_extractor import extract_text_from_docx


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract(file_path: str) -> dict:
    """
    Main entry point. Accepts a path to a .pdf or .docx file.
    Returns:
        {
            'file_name': 'filename.ext',
            'file_text': [
                {'heading': 'Section Title', 'text': 'Body text...'},
                ...
            ]
        }
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    if ext == ".pdf":
        sections = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        sections = extract_text_from_docx(file_path)

    return {
        "file_name": path.name,
        "file_text": sections,
    }
