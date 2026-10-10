"""Deterministic financial-impact scoring (docs/impact-rubrik.md).

Split for modularity (2026-10-10):
  - factors.py        -> ImpactFactors contract + FactorExtractor ABC
  - deterministic.py  -> the current extractor impl (qualitative + quantified)
  - rubric.py (this)  -> deterministic scoring only (score/explain), consuming
                         ImpactFactors. A better financial-domain extractor can
                         replace the impl without touching scoring.

Rules honored:
- Impact is magnitude only, never direction, probability, or confidence.
- Factors must be explicitly present in the text; nothing is invented.
- Abstention (None) when no magnitude evidence exists.
- Final score is computed by deterministic code, not a model.
"""

from app.impact.deterministic import extract_factors
from app.impact.factors import FactorExtractor, ImpactFactors

__all__ = ["ImpactFactors", "FactorExtractor", "extract_factors", "score", "explain"]


def score(factors: ImpactFactors) -> int | None:
    """Map extracted factors to a 1-10 band, or None to abstain."""
    if factors.continuity_threat:
        return 9

    # Contrast/offsetting evidence: net impact indeterminate -> abstain, unless
    # a hard anchor (a large quantified loss) exists (rubric rule 7).
    if factors.contrasting and (factors.max_loss_pct is None or factors.max_loss_pct < 20):
        return None

    if factors.max_loss_pct is None:
        # No quantified exposure. Qualitative magnitude phrases now map to a
        # band instead of abstaining (fixes "sales boom" -> null).
        if factors.qual_magnitude == "high":
            band_low = 7
        elif factors.qual_magnitude == "moderate":
            band_low = 5
        elif factors.qual_magnitude == "low":
            band_low = 3
        elif factors.breadth == "site" and not factors.persistent:
            band_low = 3  # clearly-bounded single-site event
        else:
            return None
        # Scope/persistence can still raise within limits.
        if factors.breadth == "company_wide" and band_low < 7:
            band_low = min(band_low + 2, 8)
        elif factors.persistent and band_low < 7:
            band_low = min(band_low + 1, 8)
        return band_low

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
    if factors.qual_magnitude is not None:
        parts.append(f"qualitative magnitude ({factors.qual_magnitude})")
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
