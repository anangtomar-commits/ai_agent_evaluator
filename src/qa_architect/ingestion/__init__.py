"""Deterministic document ingestion & normalization."""

from qa_architect.ingestion.models import DocSection, DocumentTree
from qa_architect.ingestion.parser import parse_document, parse_text

__all__ = ["DocSection", "DocumentTree", "parse_document", "parse_text"]
