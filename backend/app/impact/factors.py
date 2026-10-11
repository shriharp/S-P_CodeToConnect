"""Impact factor extraction: the modular contract between extraction and scoring.

Architecture (kept swappable per the 2026-10-10 direction):
  - `ImpactFactors` is the dataclass contract. Whatever extracts factors — the
    current deterministic extractor, or a future financial-domain model — must
    emit this shape.
  - `FactorExtractor` is the ABC seam. A better model-backed extractor can
    replace `DeterministicExtractor` later without touching scoring.
  - `score()` / `explain()` live in rubric.py and consume ImpactFactors only,
    so scoring stays deterministic and independent of HOW factors were found.

The current extractor reads BOTH quantified cues (percentages) and qualitative
magnitude phrases ("surge", "collapse", "record high"), with negation handling
and optional event-category context — fixing the old quant-only rubric that
abstained on purely qualitative headlines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ImpactFactors:
    max_loss_pct: float | None = None
    breadth: str | None = None  # "site" | "company_wide"
    persistent: bool = False
    continuity_threat: bool = False
    # NEW: qualitative magnitude intensity, independent of any percentage.
    qual_magnitude: str | None = None  # "high" | "moderate" | "low" | None
    # NEW: True when offsetting/mixed evidence makes the NET impact
    # indeterminate -> scoring abstains (rubric rule 7) unless a hard anchor.
    contrasting: bool = False
    evidence: list[str] = field(default_factory=list)


class FactorExtractor(ABC):
    """Seam for factor extraction. A financial-domain model can implement this."""

    @abstractmethod
    def extract(self, text: str, event_category: str | None = None) -> ImpactFactors: ...
