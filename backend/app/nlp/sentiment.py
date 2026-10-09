"""Company-specific sentiment scoring (lexicon layer; model-backed swap-in later)."""

from app.core.signal_contract import EvidenceExcerpt, EvidenceSupports
from app.nlp.excerpts import sentence_excerpts

NEGATIVE_CUES = (
    "miss", "fall", "fell", "drop", "dropped", "decline", "lawsuit", "fine",
    "downgrade", "default", "recall", "outage", "shutdown", "disrupt", "loss",
    "misses", "plunge", "slump", "warn", "cuts", "cut revenue", "layoff", "probe",
)
POSITIVE_CUES = (
    "beat", "rise", "rose", "gain", "record", "upgrade", "launch", "win",
    "agreement", "partnership", "expand", "growth", "profit", "surge", "approve",
)


def score_sentiment(text: str) -> tuple[float | None, list[EvidenceExcerpt]]:
    """Return (score in [-1, 1] or None when no directional evidence, excerpts)."""
    lower = text.lower()
    neg = sum(1 for c in NEGATIVE_CUES if c in lower)
    pos = sum(1 for c in POSITIVE_CUES if c in lower)
    if neg == 0 and pos == 0:
        return None, []
    raw = (pos - neg) / max(pos + neg, 1)
    score = round(max(-1.0, min(1.0, raw)), 3)
    cues = NEGATIVE_CUES if score < 0 else POSITIVE_CUES
    excerpts = sentence_excerpts(text, list(cues), EvidenceSupports.sentiment)
    return score, excerpts
