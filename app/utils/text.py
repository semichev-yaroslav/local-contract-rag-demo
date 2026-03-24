from __future__ import annotations

import re
from typing import List


ORG_PATTERN = re.compile(
    r"(?:(?:ООО|АО|ПАО|ЗАО|ОАО|ИП)\s*[\"«„“][^\"»“”\n]+[\"»“”])|"
    r"(?:(?:ООО|АО|ПАО|ЗАО|ОАО|ИП)\s+[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9\s().,-]{1,80})"
)


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def strip_quotes(value: str) -> str:
    return value.replace("«", "").replace("»", "").replace('"', "").strip()


def normalize_counterparty(value: str) -> str:
    value = compact_whitespace(value)
    value = strip_quotes(value)
    value = re.sub(r"\s*\([^)]*\)", "", value)
    value = value.upper()
    return compact_whitespace(value)


def extract_organizations(text: str) -> List[str]:
    found = []
    seen = set()
    for match in ORG_PATTERN.finditer(text):
        org = compact_whitespace(match.group(0).rstrip(".,;:"))
        normalized = normalize_counterparty(org)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        found.append(org)
    return found
