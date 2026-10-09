"""Shared evidence-excerpt extraction: exact sentences from retained source text."""

import re

from app.core.signal_contract import EvidenceExcerpt, EvidenceSupports


def sentence_excerpts(
    text: str, keywords: list[str], supports: EvidenceSupports
) -> list[EvidenceExcerpt]:
    excerpts: list[EvidenceExcerpt] = []
    seen: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lower = sentence.lower()
        if any(k in lower for k in keywords) and sentence.strip() not in seen:
            seen.add(sentence.strip())
            excerpts.append(EvidenceExcerpt(text=sentence.strip(), supports={supports}))
    return excerpts
