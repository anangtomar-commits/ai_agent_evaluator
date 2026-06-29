import pdfplumber


def extract_text_from_pdf(file_path: str) -> list[dict]:
    """
    Extracts text section-wise from a PDF file.
    Headings are detected by font size being larger than the median body font size.
    Returns a list of {'heading': ..., 'text': ..., 'page_start': int, 'page_end': int} dicts.
    [Page N] markers are embedded in the text at every page boundary.
    """
    sections = []
    current_heading = "Introduction"
    current_text: list[str] = []
    current_page_start = 1
    current_page_end = 1

    with pdfplumber.open(file_path) as pdf:
        all_chars = []
        for page in pdf.pages:
            if page.chars:
                all_chars.extend(page.chars)

        if not all_chars:
            return [{"heading": "Document", "text": "", "page_start": 1, "page_end": 1}]

        font_sizes = [c["size"] for c in all_chars if c.get("size")]
        if not font_sizes:
            return [{"heading": "Document", "text": "", "page_start": 1, "page_end": 1}]

        font_sizes_sorted = sorted(font_sizes)
        median_size = font_sizes_sorted[len(font_sizes_sorted) // 2]
        heading_threshold = median_size * 1.15

        for page_num, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(extra_attrs=["size", "fontname"])
            if not words:
                continue

            line_groups = _group_words_into_lines(words)
            page_marker_added = False  # emit [Page N] once per page, before first body line

            for line in line_groups:
                avg_size = sum(w.get("size", 0) for w in line) / len(line)
                line_text = " ".join(w["text"] for w in line).strip()

                if not line_text:
                    continue

                if avg_size >= heading_threshold and len(line_text) < 120:
                    if current_text or sections:
                        sections.append({
                            "heading": current_heading,
                            "text": " ".join(current_text).strip(),
                            "page_start": current_page_start,
                            "page_end": current_page_end,
                        })
                    current_heading = line_text
                    current_text = []
                    current_page_start = page_num
                    current_page_end = page_num
                    page_marker_added = False
                else:
                    if not page_marker_added:
                        current_text.append(f"[Page {page_num}]")
                        page_marker_added = True
                    current_text.append(line_text)
                    current_page_end = page_num

    if current_text or not sections:
        sections.append({
            "heading": current_heading,
            "text": " ".join(current_text).strip(),
            "page_start": current_page_start,
            "page_end": current_page_end,
        })

    return sections


def _group_words_into_lines(words: list[dict], y_tolerance: float = 3.0) -> list[list[dict]]:
    """Groups extracted words into lines based on their vertical position."""
    if not words:
        return []

    lines = []
    current_line = [words[0]]

    for word in words[1:]:
        prev_y = current_line[-1].get("top", 0)
        curr_y = word.get("top", 0)
        if abs(curr_y - prev_y) <= y_tolerance:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]

    lines.append(current_line)
    return lines
