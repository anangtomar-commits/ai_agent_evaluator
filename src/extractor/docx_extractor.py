from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


_HEADING_STYLES = {
    "heading 1", "heading 2", "heading 3",
    "heading 4", "heading 5", "heading 6",
    "title", "subtitle",
}


def extract_text_from_docx(file_path: str) -> list[dict]:
    """
    Extracts text section-wise from a .docx file, preserving tables.
    Walks the document body in order so tables appear in the right section.
    Returns a list of {'heading': ..., 'text': ...} dicts.
    """
    doc = Document(file_path)

    sections = []
    current_heading = None
    current_blocks = []  # list of text strings (paragraphs + rendered tables)

    for block in _iter_body_blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue

            style_name = block.style.name.lower() if block.style and block.style.name else ""

            if style_name in _HEADING_STYLES:
                if current_heading is not None:
                    sections.append({
                        "heading": current_heading,
                        "text": "\n".join(current_blocks).strip(),
                    })
                current_heading = text
                current_blocks = []
            else:
                current_blocks.append(text)

        elif isinstance(block, Table):
            rendered = _render_table(block)
            if rendered:
                current_blocks.append(rendered)

    # Flush last section
    if current_heading is not None:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_blocks).strip(),
        })
    elif current_blocks:
        sections.append({
            "heading": "Document",
            "text": "\n".join(current_blocks).strip(),
        })

    return sections


def _iter_body_blocks(doc: Document):
    """
    Yields Paragraph and Table objects in document order.
    doc.paragraphs skips tables; iterating doc.element.body preserves order.
    """
    for child in doc.element.body:
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def _render_table(table: Table) -> str:
    """
    Renders a docx Table as a markdown-style pipe table.
    The first row is treated as the header row.
    Merged/empty cells are included as empty strings.
    """
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append(cells)

    if not rows:
        return ""

    # Deduplicate horizontally-merged cells (python-docx repeats merged cell text)
    rows = [_dedup_merged_cells(row) for row in rows]

    col_count = max(len(r) for r in rows)
    rows = [r + [""] * (col_count - len(r)) for r in rows]

    col_widths = [max(len(r[i]) for r in rows) for i in range(col_count)]

    def fmt_row(cells):
        return "| " + " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(cells)) + " |"

    lines = [fmt_row(rows[0])]
    lines.append("| " + " | ".join("-" * w for w in col_widths) + " |")
    for row in rows[1:]:
        lines.append(fmt_row(row))

    return "\n".join(lines)


def _dedup_merged_cells(cells: list[str]) -> list[str]:
    """
    python-docx repeats the same text for horizontally merged cells.
    Replace consecutive duplicates with an empty string.
    """
    result = []
    for i, cell in enumerate(cells):
        if i > 0 and cell == cells[i - 1]:
            result.append("")
        else:
            result.append(cell)
    return result
