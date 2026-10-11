"""Deterministic impact factor extractor (current FactorExtractor impl).

Improves on the old quant-only extractor with three things:
  1. Qualitative magnitude phrases ("surge", "collapse", "record high") so
     purely qualitative headlines score instead of abstaining.
  2. Negation handling: "no significant decline", "avoided a loss" do NOT
     count as magnitude evidence.
  3. Event context: the event category is accepted as an optional hint (e.g. a
     credit default is inherently high-magnitude) but never fabricates — it only
     raises a reading that has SOME supporting signal already.

Scoring stays deterministic (rubric.py). This module only finds factors; it
never assigns the final 1-10 score itself.
"""

import re

from app.impact.factors import FactorExtractor, ImpactFactors

_URL_RE = re.compile(r"https?://\S+|www\.\S+")

# ---- Quantified magnitude (percentages), unchanged in spirit ----
PCT_PATTERNS = (
    r"(?:cut|fell|fell by|down|drop(?:ped)?(?: by)?|declin(?:e|ed)(?: by)?|"
    r"loss(?:es)? of|slump(?:ed)?(?: by)?|plunge(?:d)?(?: by)?|)"
    r"\s*(-?\d+(?:\.\d+)?)\s*(?:%|percent)",
    r"(-?\d+(?:\.\d+)?)\s*%\s*(?:drop|decline|fall|loss|cut)",
)

# ---- Qualitative magnitude phrases, tiered by intensity ----
# Each tier maps to a scoring band. Direction (up/down) is irrelevant to impact
# (magnitude only), so positive and negative phrases both count.
QUAL_HIGH = (
    "surge", "surged", "soar", "soared", "plunge", "plunged", "plummet",
    "plummeted", "collapse", "collapsed", "crater", "cratered", "spike",
    "spiked", "skyrocket", "skyrocketed", "record high", "record low",
    "all-time high", "all-time low", "record profit", "record loss",
    "historic", "unprecedented", "tumble", "tumbled", "slump", "slumped",
    "boom", "boomed", "crash", "crashed",
)
QUAL_MODERATE = (
    "jump", "jumped", "leap", "leaped", "rally", "rallied", "rebound",
    "rebounded", "climb", "climbed", "slide", "slid", "dropped sharply",
    "fell sharply", "rose sharply", "gained sharply", "swung",
)
QUAL_LOW = (
    "edged up", "edged down", "dipped", "dip", "ticked up", "ticked down",
    "nudged", "slipped", "slip", "eased", "ease",
    # NOTE: pure no-change words ("flat", "unchanged", "held steady") are
    # deliberately excluded — they describe absence of movement (neutral), not
    # a small-but-real impact, so they must abstain rather than score low.
)

# Contrast cues: offsetting/mixed evidence means the NET impact is
# indeterminate -> abstain (rubric rule 7), unless a hard anchor exists.
CONTRAST_CUES = (
    "offset", "offset by", "offsetting", "partially offset", "balanced by",
    "countered by", "mitigated by", "offset the",
)

# ---- Negation cues: suppress a magnitude phrase if nearby ----
NEGATION_CUES = (
    "no ", "not ", "never", "avoid", "avoided", "avert", "averted",
    "prevent", "prevented", "without", "lack", "lacking", "no significant",
    "no major", "no material", "did not", "does not", "has not", "had not",
    "won't", "will not", "would not", "couldn't", "could not",
)

# ---- Breadth / scope cues ----
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
    "for years", "indefinitely", "several years", "lasting", "sustained",
)

CONTINUITY_CUES = (
    "bankrupt", "insolven", "default", "cannot pay", "unable to pay",
    "cease operations", "wind down", "solvency", "liquidat",
)

# Event-category context: only raises a reading that already has SOME signal.
# Never assigns a magnitude from category alone (no fabrication).
HIGH_SEVERITY_EVENTS = {"credit_event", "regulatory_or_legal"}


def _is_negated(text: str, match_start: int) -> bool:
    """True if a negation cue appears within ~40 chars before the match."""
    window = text[max(0, match_start - 40):match_start]
    return any(neg in window for neg in NEGATION_CUES)


class DeterministicExtractor(FactorExtractor):
    def extract(self, text: str, event_category: str | None = None) -> ImpactFactors:
        # Strip URLs so CDN paths never count as evidence.
        lower = _URL_RE.sub(" ", text.lower())
        factors = ImpactFactors()

        # 1) Quantified percentages (unchanged).
        pcts: list[float] = []
        for pattern in PCT_PATTERNS:
            for match in re.finditer(pattern, lower):
                pcts.append(abs(float(match.group(1))))
                factors.evidence.append(match.group(0).strip())
        if pcts:
            factors.max_loss_pct = max(pcts)

        # 2) Qualitative magnitude phrases, tiered, with negation handling.
        if not pcts:  # only read qualitative if no hard number already anchors it
            qual = self._qualitative_magnitude(lower)
            if qual:
                factors.qual_magnitude, phrase = qual
                factors.evidence.append(phrase)

        # 3) Breadth cues.
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

        # 4) Duration.
        for cue in DURATION_PERSISTENT:
            if cue in lower:
                factors.persistent = True
                factors.evidence.append(f"duration: {cue}")
                break

        # 5) Continuity (solvency) cues.
        for cue in CONTINUITY_CUES:
            if cue in lower:
                factors.continuity_threat = True
                factors.evidence.append(f"continuity: {cue}")
                break

        # 6) Contrast cues: offsetting/mixed evidence -> net impact indeterminate.
        for cue in CONTRAST_CUES:
            if cue in lower:
                factors.contrasting = True
                factors.evidence.append(f"contrast: {cue}")
                break

        # 6) Event context: raise an existing qualitative reading for inherently
        #    high-severity categories, but only if some magnitude signal exists.
        if (event_category in HIGH_SEVERITY_EVENTS
                and factors.qual_magnitude == "moderate"
                and factors.continuity_threat):
            factors.qual_magnitude = "high"
            factors.evidence.append(f"event-context: {event_category} + continuity")

        return factors

    def _qualitative_magnitude(self, lower: str) -> tuple[str, str] | None:
        """Return (intensity, matched_phrase) for the strongest non-negated hit."""
        for tier, cues in (("high", QUAL_HIGH), ("moderate", QUAL_MODERATE),
                           ("low", QUAL_LOW)):
            for cue in cues:
                for m in re.finditer(rf"\b{re.escape(cue)}\b", lower):
                    if not _is_negated(lower, m.start()):
                        return tier, cue
        return None


# Module-level default instance so callers can keep using a simple function.
_extract = DeterministicExtractor()


def extract_factors(text: str, event_category: str | None = None) -> ImpactFactors:
    """Back-compat wrapper: run the default deterministic extractor."""
    return _extract.extract(text, event_category)
