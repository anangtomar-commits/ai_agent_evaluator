CHUNK_SIZE = 6000    # target tokens per chunk
OVERLAP = 600        # token overlap between consecutive chunks

# 1 token ≈ 4 characters for English text (OpenAI convention)
_CHARS_PER_TOKEN = 4
_CHUNK_CHARS = CHUNK_SIZE * _CHARS_PER_TOKEN    # 24 000
_OVERLAP_CHARS = OVERLAP * _CHARS_PER_TOKEN     # 2 400


def chunk_sections(sections: list[dict]) -> list[str]:
    """
    Accepts extracted sections as [{heading: text}, ...].
    Combines them into a single document string (with headings preserved),
    then splits into ~6 000-token chunks with 600-token overlap.
    Token counts are approximated as len(text) / 4 (4 chars ≈ 1 token).
    """
    full_text = _combine_sections(sections)
    if not full_text:
        return []
    return _split_into_chunks(full_text)


def _combine_sections(sections: list[dict]) -> str:
    """Joins sections into one string, keeping headings as context markers."""
    parts = []
    for section in sections:
        for heading, text in section.items():
            parts.append(f"## {heading}\n{text}")
    return "\n\n".join(parts)


def _split_into_chunks(text: str) -> list[str]:
    """
    Splits text into chunks of _CHUNK_CHARS characters with _OVERLAP_CHARS overlap.
    Splits are made at the nearest whitespace to avoid cutting mid-word.
    """
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + _CHUNK_CHARS, length)

        # Snap end to nearest whitespace (avoid cutting mid-word)
        if end < length:
            snap = text.rfind(" ", start, end)
            if snap != -1:
                end = snap

        chunks.append(text[start:end].strip())

        if end >= length:
            break

        # Step forward by chunk size minus overlap
        start = end - _OVERLAP_CHARS
        # Snap start forward past any leading whitespace
        while start < length and text[start] == " ":
            start += 1

    return chunks
