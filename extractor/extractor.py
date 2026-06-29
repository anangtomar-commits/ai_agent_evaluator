from pathlib import Path

from extractor.pdf_extractor import extract_text_from_pdf
from extractor.docx_extractor import extract_text_from_docx
from extractor.chunker import chunk_sections

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract(file_path: str, original_name: str = None) -> dict:
    """
    Main entry point. Accepts a path to a .pdf or .docx file.
    Returns:
        {
            'filename.ext': ['chunk 1 text', 'chunk 2 text', ...]
        }
    Each chunk is ~6000 tokens with a 600-token overlap with the next chunk.
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

    # sections: [{'heading': ..., 'text': ...}, ...]
    # convert to [{heading: text}, ...] then chunk
    sections_as_dicts = [{s["heading"]: s["text"]} for s in sections]
    chunks = chunk_sections(sections_as_dicts)

    file_name = original_name or path.name
    return {file_name: chunks}
