"""Parse a BRD into a normalized, section-chunked DocumentTree.

Markdown / plain text are handled natively. PDF and DOCX are supported when the
optional ``docs`` extra (pymupdf / python-docx) is installed.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from qa_architect.ingestion.models import DocSection, DocumentTree

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def _doc_id(name: str, content: str) -> str:
    digest = hashlib.sha1(f"{name}:{content}".encode("utf-8")).hexdigest()[:12]
    return f"doc-{digest}"


def _sections_from_markdown(doc_id: str, text: str) -> list[DocSection]:
    """Split markdown/plaintext into sections keyed by ATX headings.

    Content before the first heading becomes a synthetic 'preamble' section.
    Character offsets are tracked against the raw text for provenance.
    """
    sections: list[DocSection] = []
    lines = text.splitlines(keepends=True)

    cur_heading: str | None = None
    cur_level = 0
    cur_start = 0
    buf: list[str] = []
    offset = 0
    seq = 0

    def flush(end: int) -> None:
        nonlocal seq
        body = "".join(buf).strip()
        if not body and cur_heading is None:
            return
        seq += 1
        sections.append(
            DocSection(
                section_id=f"{doc_id}-s{seq:03d}",
                heading=cur_heading,
                level=cur_level,
                text=body,
                char_start=cur_start,
                char_end=end,
            )
        )

    for line in lines:
        match = _HEADING_RE.match(line.rstrip("\n"))
        if match:
            flush(offset)
            cur_heading = match.group(2).strip()
            cur_level = len(match.group(1))
            cur_start = offset
            buf = []
        else:
            buf.append(line)
        offset += len(line)

    flush(offset)
    return sections


def _read_pdf(path: Path) -> tuple[str, list[DocSection], str]:
    try:
        import fitz  # pymupdf
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError(
            "PDF ingestion requires the 'docs' extra: pip install 'qa-architect[docs]'"
        ) from exc

    doc = fitz.open(path)
    parts: list[str] = []
    page_texts: list[str] = []
    for page in doc:
        ptext = page.get_text()
        page_texts.append(ptext)
        parts.append(ptext)
    raw = "\n".join(parts)
    doc_id = _doc_id(path.name, raw)
    sections: list[DocSection] = []
    offset = 0
    for i, ptext in enumerate(page_texts, start=1):
        start = offset
        offset += len(ptext) + 1
        sections.append(
            DocSection(
                section_id=f"{doc_id}-p{i:03d}",
                heading=f"Page {i}",
                level=1,
                text=ptext.strip(),
                page=i,
                char_start=start,
                char_end=offset,
            )
        )
    return raw, sections, doc_id


def _read_docx(path: Path) -> tuple[str, list[DocSection], str]:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError(
            "DOCX ingestion requires the 'docs' extra: pip install 'qa-architect[docs]'"
        ) from exc

    document = docx.Document(str(path))
    md_lines: list[str] = []
    for para in document.paragraphs:
        style = (para.style.name or "").lower() if para.style else ""
        text = para.text.strip()
        if not text:
            continue
        if style.startswith("heading"):
            level = "".join(ch for ch in style if ch.isdigit()) or "1"
            md_lines.append(f"{'#' * int(level)} {text}")
        else:
            md_lines.append(text)
    raw = "\n".join(md_lines)
    doc_id = _doc_id(path.name, raw)
    return raw, _sections_from_markdown(doc_id, raw), doc_id


def parse_text(text: str, *, name: str = "inline.md", media_type: str = "text/markdown") -> DocumentTree:
    """Parse raw markdown/plaintext content into a DocumentTree."""
    doc_id = _doc_id(name, text)
    return DocumentTree(
        doc_id=doc_id,
        source_name=name,
        media_type=media_type,
        raw_text=text,
        sections=_sections_from_markdown(doc_id, text),
    )


def parse_bytes(data: bytes, *, name: str) -> DocumentTree:
    """Parse uploaded bytes, dispatching on the file extension in ``name``."""
    suffix = Path(name).suffix.lower()
    if suffix in {".md", ".markdown", ".txt", ""}:
        text = data.decode("utf-8", errors="replace")
        media = "text/markdown" if suffix in {".md", ".markdown"} else "text/plain"
        return parse_text(text, name=name, media_type=media)
    # Binary formats need a real path for the underlying libraries.
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return parse_document(path=str(tmp_path), name=name)
    finally:
        tmp_path.unlink(missing_ok=True)


def parse_document(path: str, *, name: str | None = None) -> DocumentTree:
    """Parse a BRD file from disk into a DocumentTree."""
    p = Path(path)
    source_name = name or p.name
    suffix = p.suffix.lower()

    if suffix in {".md", ".markdown", ".txt"}:
        text = p.read_text(encoding="utf-8", errors="replace")
        media = "text/markdown" if suffix in {".md", ".markdown"} else "text/plain"
        return parse_text(text, name=source_name, media_type=media)

    if suffix == ".pdf":
        raw, sections, doc_id = _read_pdf(p)
        return DocumentTree(
            doc_id=doc_id,
            source_name=source_name,
            media_type="application/pdf",
            raw_text=raw,
            sections=sections,
        )

    if suffix in {".docx"}:
        raw, sections, doc_id = _read_docx(p)
        return DocumentTree(
            doc_id=doc_id,
            source_name=source_name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            raw_text=raw,
            sections=sections,
        )

    raise ValueError(f"Unsupported document type: {suffix!r} ({source_name})")
