from __future__ import annotations

import re

from app.models import QueryIntent
from app.utils.text import extract_organizations, normalize_counterparty


def _extract_counterparty(question: str) -> str:
    organizations = extract_organizations(question)
    if organizations:
        return organizations[0]
    match = re.search(r"с\s+([A-Za-zА-Яа-я0-9\"«»().\s-]{3,80})", question, re.IGNORECASE)
    if match:
        return match.group(1).strip(" ?.")
    return ""


def classify_question(question: str) -> QueryIntent:
    normalized_question = question.lower()
    counterparty = _extract_counterparty(question)
    normalized_counterparty = normalize_counterparty(counterparty) if counterparty else ""

    if "следующ" in normalized_question and "прилож" in normalized_question:
        return QueryIntent(
            name="next_appendix_number",
            counterparty=counterparty,
            normalized_counterparty=normalized_counterparty,
            doc_type_hint="appendix",
        )
    if "постоплат" in normalized_question or (
        "услов" in normalized_question and "оплат" in normalized_question
    ):
        return QueryIntent(
            name="payment_terms",
            counterparty=counterparty,
            normalized_counterparty=normalized_counterparty,
            section_hint="оплат",
        )
    if ("номер" in normalized_question or "дата" in normalized_question) and "договор" in normalized_question:
        return QueryIntent(
            name="contract_details",
            counterparty=counterparty,
            normalized_counterparty=normalized_counterparty,
            doc_type_hint="contract",
        )
    if "подписан" in normalized_question and ("договор" in normalized_question or "соглашени" in normalized_question):
        return QueryIntent(
            name="signed_contract_exists",
            counterparty=counterparty,
            normalized_counterparty=normalized_counterparty,
        )
    if "есть ли" in normalized_question and ("договор" in normalized_question or "соглашени" in normalized_question):
        return QueryIntent(
            name="contract_exists",
            counterparty=counterparty,
            normalized_counterparty=normalized_counterparty,
        )
    return QueryIntent(
        name="semantic_qa",
        counterparty=counterparty,
        normalized_counterparty=normalized_counterparty,
    )
