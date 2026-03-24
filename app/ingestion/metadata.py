from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models import ContractDocument, RawDocument
from app.utils.text import compact_whitespace, extract_organizations, normalize_counterparty


DOC_TYPE_PATTERNS = [
    ("appendix", re.compile(r"\bприложени[ея]\b", re.IGNORECASE)),
    (
        "supplementary_agreement",
        re.compile(r"\bдополнительн(?:ое|ого)\s+соглашени[ея]\b", re.IGNORECASE),
    ),
    ("service_agreement", re.compile(r"\bсоглашени[ея]\b", re.IGNORECASE)),
    ("contract", re.compile(r"\bдоговор[ауе]?\b", re.IGNORECASE)),
]

DOC_NUMBER_PATTERNS = [
    re.compile(
        r"(?:договор|соглашение|приложение)[^№\n]{0,30}№\s*([A-Za-zА-Яа-я0-9/\-.]+)",
        re.IGNORECASE,
    ),
    re.compile(r"№\s*([A-Za-zА-Яа-я0-9/\-.]+)"),
]

DATE_PATTERNS = [
    re.compile(r"от\s+(\d{2}\.\d{2}\.\d{4})", re.IGNORECASE),
    re.compile(
        r"(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})",
        re.IGNORECASE,
    ),
]

PARENT_CONTRACT_PATTERN = re.compile(
    r"к\s+договор[ауе]?\s+№\s*([A-Za-zА-Яа-я0-9/\-.]+)", re.IGNORECASE
)
APPENDIX_NUMBER_PATTERN = re.compile(r"приложени[ея]\s+№\s*(\d+)", re.IGNORECASE)


def detect_doc_type(text: str) -> str:
    head = "\n".join(text.splitlines()[:20])
    for value, pattern in DOC_TYPE_PATTERNS:
        if pattern.search(head):
            return value
    return "unknown"


def find_first(patterns, text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return compact_whitespace(match.group(1))
    return ""


def detect_counterparty(text: str, overrides: Optional[Dict[str, object]] = None) -> str:
    if overrides and overrides.get("counterparty_raw"):
        return str(overrides["counterparty_raw"])
    organizations = extract_organizations(text[:4000])
    return organizations[0] if organizations else ""


def detect_signed_status(text: str, overrides: Optional[Dict[str, object]] = None) -> str:
    if overrides and overrides.get("signed_status"):
        return str(overrides["signed_status"])
    if re.search(r"подписан[оы]?\s+электронной\s+подписью", text, re.IGNORECASE):
        return "signed"
    return "unknown"


def extract_metadata(
    raw_document: RawDocument, overrides: Optional[Dict[str, object]] = None
) -> ContractDocument:
    text = raw_document.full_text
    doc_type = (
        str(overrides.get("doc_type"))
        if overrides and overrides.get("doc_type")
        else detect_doc_type(text)
    )
    doc_number = (
        str(overrides.get("doc_number"))
        if overrides and overrides.get("doc_number")
        else find_first(DOC_NUMBER_PATTERNS, text[:2000])
    )
    doc_date = (
        str(overrides.get("doc_date"))
        if overrides and overrides.get("doc_date")
        else find_first(DATE_PATTERNS, text[:2500])
    )
    counterparty_raw = detect_counterparty(text, overrides)
    parent_contract_match = PARENT_CONTRACT_PATTERN.search(text)
    parent_contract_number = ""
    if overrides and overrides.get("parent_contract_number"):
        parent_contract_number = str(overrides["parent_contract_number"])
    elif parent_contract_match:
        parent_contract_number = compact_whitespace(parent_contract_match.group(1))
    appendix_number_match = APPENDIX_NUMBER_PATTERN.search(text[:1500])
    appendix_number = None
    if overrides and overrides.get("appendix_number") is not None:
        appendix_number = int(overrides["appendix_number"])
    elif appendix_number_match:
        appendix_number = int(appendix_number_match.group(1))

    confidence_components = [
        bool(doc_type and doc_type != "unknown"),
        bool(counterparty_raw),
        bool(doc_number),
        bool(doc_date),
    ]
    extraction_confidence = sum(confidence_components) / len(confidence_components)

    return ContractDocument(
        doc_id=str(uuid.uuid4()),
        source_path=raw_document.source_path,
        file_name=raw_document.file_name,
        sha256=raw_document.sha256,
        doc_type=doc_type,
        counterparty_raw=counterparty_raw,
        counterparty_normalized=normalize_counterparty(counterparty_raw),
        doc_number=doc_number,
        doc_date=doc_date,
        parent_contract_number=parent_contract_number,
        appendix_number=appendix_number,
        signed_status=detect_signed_status(text, overrides),
        full_text=text,
        extraction_confidence=extraction_confidence,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
