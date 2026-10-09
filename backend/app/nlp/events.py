"""Primary event classification (lexicon layer; model-backed swap-in later)."""

import re

from app.core.signal_contract import EventCategory, EvidenceExcerpt, EvidenceSupports
from app.nlp.excerpts import sentence_excerpts

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


def classify_event(text: str) -> tuple[EventCategory, list[EvidenceExcerpt]]:
    lower = text.lower()
    scores: dict[EventCategory, int] = {}
    for category, patterns in EVENT_PATTERNS.items():
        hits = sum(1 for p in patterns if re.search(p, lower))
        if hits:
            scores[category] = hits
    if not scores:
        return EventCategory.unknown, []
    best = max(scores.items(), key=lambda kv: (kv[1], kv[0].value))
    category = best[0]
    keywords = [p for p in EVENT_PATTERNS[category] if re.search(p, lower)]
    return category, sentence_excerpts(text, keywords, EvidenceSupports.event)
