"""Normalized document representation produced by ingestion."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocSection(BaseModel):
    section_id: str
    heading: str | None = None
    level: int = 0
    text: str = ""
    page: int | None = None
    char_start: int = 0
    char_end: int = 0


class DocumentTree(BaseModel):
    doc_id: str
    source_name: str
    media_type: str
    raw_text: str
    sections: list[DocSection] = Field(default_factory=list)

    @property
    def char_count(self) -> int:
        return len(self.raw_text)
