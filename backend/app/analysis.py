"""Company-specific analysis: sentiment + event classification + evidence extraction.

CPU-first, no paid APIs. MVP uses a compact lexicon/trigger layer; model-backed
refinement (e.g. a small finbert-style transformer) slots in behind the same
Analyzer interface and is benchmarked before adoption (docs/architecture.md).
"""

import re

from app.signal_contract import (
    AnalysisStatus,
    EventCategory,
    EvidenceExcerpt,
    EvidenceSupports,
    QualityFlag,
)

EVENT_PATTERNS: dict[EventCategory, tuple[str, ...]] = {
    EventCategory.earnings: (r"earnings?", r"quarterly results?", r"revenue (miss|beat)", r"guidance"),
    EventCategory.operational_disruption: (r"shutdown", r"outage", r"disrupt", r"recall", r"halt(?:ed)?"),
    EventCategory.merger_or_acquisition: (r"\bacquisition\b", r"\bmerger\b", r"to buy", r"takeover", r"acquire[sd]?"),
    EventCategory.regulatory_or_legal: (r"lawsuit", r"fine[sd]?", r"regulator", r"antitrust", r"investigat", r"sanction"),
    EventCategory.credit_event: (r"default", r"bankruptc", r"downgrade", r"credit rating", r"insolven"),
    EventCategory.product_launch: (r"launch(?:es|ed)?", r"unveil(?:s|ed)?", r"new product", r"release[sd]?"),
    EventCategory.commercial_agreement: (r"partnership", r"contract win", r"agreement with", r"supply deal", r"joint venture"),
    EventCategory.geopolitical: (r"tariff", r"war\b", r"conflict", r"geopolitic", r"export ban"),
    EventCategory.macroeconomic: (r"inflation", r"interest rate", r"gdp", r"recession", r"central bank"),
}

NEGATIVE_CUES = (
    "miss", "fall", "fell", "drop", "dropped", "decline", "lawsuit", "fine",
    "downgrade", "default", "recall", "outage", "shutdown", "disrupt", "loss",
    "misses", "plunge", "slump", "warn", "cuts", "cut revenue", "layoff", "probe",
)
POSITIVE_CUES = (
    "beat", "rise", "rose", "gain", "record", "upgrade", "launch", "win",
    "agreement", "partnership", "expand", "growth", "profit", "surge", "approve",
)

def _sentence_excerpts(text: str, keywords: list[str], supports: EvidenceSupports) -> list[EvidenceExcerpt]:
    excerpts: list[EvidenceExcerpt] = []
    seen: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lower = sentence.lower()
        if any(k in lower for k in keywords) and sentence.strip() not in seen:
            seen.add(sentence.strip())
            excerpts.append(EvidenceExcerpt(text=sentence.strip(), supports={supports}))
    return excerpts


def classify_event(text: str) -> tuple[EventCategory, list[EvidenceExcerpt]]:
    lower = text.lower()
    scores: dict[EventCategory, int] = {}
    for category, patterns in EVENT_PATTERNS.items():
        hits = sum(1 for p in patterns if re.search(p, lower))
        if hits:
            scores[category] = hits
    if not scores:
        return EventCategory.unknown, []
    # Tie broken by taxonomy order stability: max by hits then category name.
    best = max(scores.items(), key=lambda kv: (kv[1], kv[0].value))
    category = best[0]
    keywords = [p for p in EVENT_PATTERNS[category] if re.search(p, lower)]
    return category, _sentence_excerpts(text, keywords, EvidenceSupports.event)


def sentiment(text: str) -> tuple[float | None, list[EvidenceExcerpt]]:
    lower = text.lower()
    neg = sum(1 for c in NEGATIVE_CUES if c in lower)
    pos = sum(1 for c in POSITIVE_CUES if c in lower)
    if neg == 0 and pos == 0:
        return None, []
    raw = (pos - neg) / max(pos + neg, 1)
    score = round(max(-1.0, min(1.0, raw)), 3)
    cues = NEGATIVE_CUES if score < 0 else POSITIVE_CUES
    excerpts = _sentence_excerpts(text, list(cues), EvidenceSupports.sentiment)
    return score, excerpts


def analyze(text: str, source_item_id: str, provider: str, provenance: str) -> "RiskSignal":
    """Return a RiskSignal for one detected company mention.

    MVP scope: single-company text. Multi-company splitting lands with ingestion.
    """
    from datetime import datetime, timezone

    from app.signal_contract import Provenance, RiskSignal, SourceType, validate_evidence_membership

    now = datetime.now(timezone.utc)
    event_category, event_excerpts = classify_event(text)
    senti_score, senti_excerpts = sentiment(text)

    excerpts = event_excerpts + senti_excerpts
    flags: set[QualityFlag] = {QualityFlag.unresolved_company}
    if senti_score is None:
        flags.add(QualityFlag.insufficient_evidence)
    impact_score, impact_explanation = None, None  # deterministic rubric lands next
    if impact_score is None:
        flags.add(QualityFlag.insufficient_evidence)
    signal = RiskSignal(
        signal_id=f"{source_item_id}-s0",
        source_item_id=source_item_id,
        source_provider=provider,
        source_type=SourceType.news,
        published_at=now,
        ingested_at=now,
        provenance=Provenance(provenance),
        company_id="unresolved-mvp",
        company_name="unresolved-mvp",
        ticker=None,
        event_category=event_category,
        event_summary=text[:200],
        sentiment_score=senti_score,
        impact_score=impact_score,
        impact_explanation=impact_explanation,
        evidence_excerpts=excerpts,
        analysis_status=(
            AnalysisStatus.abstained if senti_score is None else AnalysisStatus.complete
        ),
        quality_flags=flags,
        analyzed_at=now,
        analysis_method_version="lexicon-0.1",
    )
    validate_evidence_membership(signal, text)
    return signal
