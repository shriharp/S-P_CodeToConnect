"""Deterministic financial-impact scoring (docs/impact-rubrik.md).

Rules honored here:
- Impact is magnitude only, never direction, probability, or confidence.
- Factors must be explicitly present in the text; nothing is invented.
- Abstention (None) whenever extracted facts could land in different bands.
- Final score is computed by deterministic code, not a model.

Factor extraction (MVP):
- magnitude: largest explicitly quantified loss/exposure percentage.
- breadth: site/partial scope vs company-wide scope cues.
- duration: explicit persistence cues (multi-year, prolonged, permanent).
"""

import re
from dataclasses import dataclass, field

_URL_RE = re.compile(r"https?://\S+|www\.\S+")

PCT_PATTERNS = (
    r"(?:cut|fell|fell by|down|drop(?:ped)?(?: by)?|declin(?:e|ed)(?: by)?|"
    r"loss(?:es)? of|slump(?:ed)?(?: by)?|plunge(?:d)?(?: by)?|)"
    r"\s*(-?\d+(?:\.\d+)?)\s*(?:%|percent)",
    r"(-?\d+(?:\.\d+)?)\s*%\s*(?:drop|decline|fall|loss|cut)",
)

BREADTH_COMPANY_WIDE = (
    "company-wide", "entire company", "all operations", "across the company",
    "whole company", "global operations", "all plants", "full-year",
)
BREADTH_SITE = (
    "one plant", "single plant", "a plant", "one site", "single site",
    "a site", "factory in", "plant in", "one facility", "a facility",
)
DURATION_PERSISTENT = (
    "multi-year", "multiyear", "permanently", "permanent", "prolonged",
    "for years", "indefinitely", "several years",
)
CONTINUITY_CUES = (
    "bankrupt", "insolven", "default", "cannot pay", "unable to pay",
    "cease operations", "wind down", "solvency", "liquidat",
)


@dataclass
class ImpactFactors:
    max_loss_pct: float | None = None
    breadth: str | None = None  # "site" | "company_wide"
    persistent: bool = False
    continuity_threat: bool = False
    evidence: list[str] = field(default_factory=list)


def extract_factors(text: str) -> ImpactFactors:
    # Strip URLs before factor extraction: a CDN path like ".../default.png"
    # is never impact evidence and would false-positive continuity cues.
    lower = _URL_RE.sub(" ", text.lower())
    factors = ImpactFactors()

    pcts: list[float] = []
    for pattern in PCT_PATTERNS:
        for match in re.finditer(pattern, lower):
            value = abs(float(match.group(1)))
            pcts.append(value)
            factors.evidence.append(match.group(0).strip())
    if pcts:
        factors.max_loss_pct = max(pcts)

    for cue in BREADTH_COMPANY_WIDE:
        if cue in lower:
            factors.breadth = "company_wide"
            factors.evidence.append(cue)
            break
    if factors.breadth is None:
        for cue in BREADTH_SITE:
            if cue in lower:
                factors.breadth = "site"
                factors.evidence.append(cue)
                break

    if any(cue in lower for cue in DURATION_PERSISTENT):
        factors.persistent = True
        factors.evidence.append("duration: persistent")

    if any(cue in lower for cue in CONTINUITY_CUES):
        factors.continuity_threat = True
        factors.evidence.append("continuity threat cue")

    return factors


def score(factors: ImpactFactors) -> int | None:
    """Map extracted factors to a 1-10 band, or None to abstain."""
    if factors.continuity_threat:
        return 9

    if factors.max_loss_pct is None:
        # No quantified exposure: only a clearly-bounded single-site,
        # non-persistent event can be scored low; anything broader abstains.
        if factors.breadth == "site" and not factors.persistent:
            return 3
        return None

    pct = factors.max_loss_pct
    if pct >= 50:
        band = (7, 8)
    elif pct >= 20:
        band = (5, 6)
    elif pct >= 5:
        band = (3, 4)
    else:
        band = (1, 2)

    # Scope/persistence qualifiers can raise within limits, never past evidence.
    low = band[0]
    if factors.breadth == "company_wide" and low < 7:
        low = min(low + 2, 8)
    elif factors.persistent and low < 7:
        low = min(low + 1, 8)

    return low  # rubric rule 4: default to the lower score in the band


def explain(factors: ImpactFactors, impact: int) -> str:
    parts = []
    if factors.max_loss_pct is not None:
        parts.append(f"quantified loss/exposure of {factors.max_loss_pct:g}%")
    if factors.breadth == "company_wide":
        parts.append("company-wide breadth")
    elif factors.breadth == "site":
        parts.append("single-site scope")
    if factors.persistent:
        parts.append("persistent duration")
    if factors.continuity_threat:
        parts.append("continuity/solvency threat cue")
    joined = "; ".join(parts) if parts else "limited bounded consequences"
    return (
        f"Deterministic rubric score {impact}/10 based on: {joined}. "
        "Magnitude only; not a prediction or confidence estimate."
    )
