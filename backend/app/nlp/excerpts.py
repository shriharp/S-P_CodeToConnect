"""Shared evidence-excerpt extraction: exact sentences from retained source text."""

import re

from app.core.signal_contract import (
    EvidenceExcerpt,
    EvidenceSupports,
    normalize_evidence_text,
)


def sentence_excerpts(
    text: str, keywords: list[str], supports: EvidenceSupports
) -> list[EvidenceExcerpt]:
    excerpts: list[EvidenceExcerpt] = []
    seen: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lower = sentence.lower()
        if any(k in lower for k in keywords) and sentence.strip() not in seen:
            seen.add(sentence.strip())
            cleaned = normalize_evidence_text(sentence)
            if len(cleaned) < 8:  # too noisy to be useful evidence
                continue
            excerpts.append(EvidenceExcerpt(text=cleaned, supports={supports}))
    return excerpts


def merge_excerpts(excerpts: list[EvidenceExcerpt]) -> list[EvidenceExcerpt]:
    """Dedupe by cleaned text, unioning supports. Turns two identical
    [sentiment]/[impact] lines into one [sentiment, impact] line."""
    by_text: dict[str, EvidenceExcerpt] = {}
    for e in excerpts:
        key = e.text.lower()
        if key in by_text:
            by_text[key].supports |= e.supports
        else:
            by_text[key] = EvidenceExcerpt(text=e.text, supports=set(e.supports))
    return list(by_text.values())
