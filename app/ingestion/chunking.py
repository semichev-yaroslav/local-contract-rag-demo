from __future__ import annotations

import re
from typing import Iterable, List

from app.models import ContractDocument, DocumentChunk
from app.utils.text import compact_whitespace


SECTION_HINTS = [
    "предмет",
    "порядок расчетов",
    "условия оплаты",
    "стоимость",
    "срок действия",
    "ответственность",
    "реквизиты",
    "приложение",
]


def is_heading(line: str) -> bool:
    normalized = compact_whitespace(line).lower()
    if not normalized:
        return False
    if len(normalized) <= 120 and any(hint in normalized for hint in SECTION_HINTS):
        return True
    if re.match(r"^\d+(\.\d+)*\s+[А-Яа-яA-Za-z]", line):
        return True
    return normalized.isupper() and len(normalized) <= 120


def _flush_chunk(
    chunks: List[DocumentChunk],
    doc_id: str,
    chunk_order: int,
    section_name: str,
    lines: Iterable[str],
) -> None:
    text = "\n".join(line for line in lines if line).strip()
    if not text:
        return
    chunks.append(
        DocumentChunk(
            chunk_id=f"{doc_id}:{chunk_order}",
            doc_id=doc_id,
            chunk_order=chunk_order,
            section_name=section_name or "general",
            text=text,
        )
    )


def chunk_document(document: ContractDocument, max_chars: int = 1000) -> List[DocumentChunk]:
    lines = [compact_whitespace(line) for line in document.full_text.splitlines()]
    lines = [line for line in lines if line]
    chunks: List[DocumentChunk] = []
    current_section = "general"
    current_lines: List[str] = []
    current_size = 0
    chunk_order = 0

    for line in lines:
        if is_heading(line):
            _flush_chunk(chunks, document.doc_id, chunk_order, current_section, current_lines)
            if current_lines:
                chunk_order += 1
            current_section = line
            current_lines = [line]
            current_size = len(line)
            continue

        if current_size + len(line) > max_chars and current_lines:
            _flush_chunk(chunks, document.doc_id, chunk_order, current_section, current_lines)
            chunk_order += 1
            current_lines = [current_section, line] if current_section != "general" else [line]
            current_size = sum(len(item) for item in current_lines)
            continue

        current_lines.append(line)
        current_size += len(line)

    _flush_chunk(chunks, document.doc_id, chunk_order, current_section, current_lines)
    return chunks
