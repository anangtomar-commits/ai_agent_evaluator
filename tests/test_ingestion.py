"""Phase 1 — ingestion / parsing."""

from qa_architect.ingestion.parser import parse_text


def test_parse_sample_sections(sample_doc):
    assert sample_doc.raw_text
    headings = [s.heading for s in sample_doc.sections if s.heading]
    assert any("Tone" in h for h in headings)
    assert any("Guardrails" in h for h in headings)
    assert any("Compliance" in h for h in headings)


def test_section_offsets_are_consistent(sample_doc):
    for section in sample_doc.sections:
        assert section.char_start <= section.char_end
        assert section.char_end <= len(sample_doc.raw_text)
        # text recovered from offsets contains the heading body when present
        if section.heading:
            slice_ = sample_doc.raw_text[section.char_start:section.char_end]
            assert section.heading in slice_


def test_parse_text_preamble_handling():
    doc = parse_text("intro line\n\n# Title\nbody", name="x.md")
    assert doc.sections[0].heading is None  # preamble captured
    assert any(s.heading == "Title" for s in doc.sections)
