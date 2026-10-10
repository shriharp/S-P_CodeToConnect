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


def keyword_scores(text: str) -> dict[EventCategory, int]:
    """Per-category keyword hit counts. Empty dict = no cue matched."""
    lower = text.lower()
    scores: dict[EventCategory, int] = {}
    for category, patterns in EVENT_PATTERNS.items():
        hits = sum(1 for p in patterns if re.search(p, lower))
        if hits:
            scores[category] = hits
    return scores


def classify_event(text: str) -> tuple[EventCategory, list[EvidenceExcerpt]]:
    scores = keyword_scores(text)
    if not scores:
        return EventCategory.unknown, []
    best = max(scores.items(), key=lambda kv: (kv[1], kv[0].value))
    category = best[0]
    keywords = [p for p in EVENT_PATTERNS[category] if re.search(p, text.lower())]
    return category, sentence_excerpts(text, keywords, EvidenceSupports.event)


def classify_event_hybrid(text: str) -> tuple[EventCategory, list[EvidenceExcerpt]]:
    """Best-of-both-worlds event classification.

    Keyword table wins on clean financial shorthand (measurably better on our
    eval set); the zero-shot model wins on paraphrase/no-cue text. So:
      1. Keyword unambiguous (one category clearly ahead) -> use keyword.
         Preserves its wins and avoids the model's finance-shorthand errors.
      2. Keyword silent (no cue) -> use the model. Catches paraphrases keyword
         would call Unknown.
      3. Keyword ambiguous (top categories tied) -> let the model break the tie.

    Evidence excerpts always come from the retained source text (never
    fabricated), whichever backend chose the category.
    """
    scores = keyword_scores(text)
    from app.nlp.event_model import classify_event_model

    model_key, _conf = classify_event_model(text)
    try:
        model_cat = EventCategory[model_key]
    except KeyError:
        model_cat = EventCategory.unknown

    if not scores:
        # No keyword cue — defer to the model (paraphrase / chatter).
        category = model_cat
    else:
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0].value))
        top_cat, top_hits = ranked[0]
        tied = [c for c, h in ranked if h == top_hits]
        if len(tied) > 1:
            # Ambiguous keyword match — let the model break the tie.
            category = model_cat if model_cat in tied else top_cat
        else:
            # Keyword unambiguous — trust it (high precision on shorthand).
            category = top_cat

    keywords = [p for p in EVENT_PATTERNS.get(category, ()) if re.search(p, text.lower())]
    excerpts = sentence_excerpts(text, keywords, EvidenceSupports.event)
    return category, excerpts
