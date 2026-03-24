from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawDocument:
    source_path: str
    file_name: str
    paragraphs: List[str]
    full_text: str
    sha256: str


@dataclass
class ContractDocument:
    doc_id: str
    source_path: str
    file_name: str
    sha256: str
    doc_type: str
    counterparty_raw: str
    counterparty_normalized: str
    doc_number: str
    doc_date: str
    parent_contract_number: str
    appendix_number: Optional[int]
    signed_status: str
    full_text: str
    extraction_confidence: float
    created_at: str
    openai_file_id: str = ""
    openai_vector_store_file_id: str = ""


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    chunk_order: int
    section_name: str
    text: str


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    file_name: str
    section_name: str
    text: str
    score: float


@dataclass
class QueryIntent:
    name: str
    counterparty: str = ""
    normalized_counterparty: str = ""
    doc_type_hint: str = ""
    section_hint: str = ""


@dataclass
class SearchAnswer:
    question: str
    intent: str
    answer: str
    sources: List[RetrievedChunk] = field(default_factory=list)
    used_llm: bool = False
