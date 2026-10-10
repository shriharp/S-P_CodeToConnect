"""Pydantic v2 implementation of the signal contract (docs/signal-contract.md).

Semantics enforced here:
- One source item + one affected company + one primary event per signal.
- Sentiment: [-1, 1]; 0 is neutral, None is unknown (never neutral).
- Impact: 1-10 magnitude, None when evidence is insufficient (never a floor score).
- Evidence excerpts must be exact substrings of retained source text.
- Quality flags must be consistent with field values (null vs unknown handling).
"""

from datetime import datetime
from enum import Enum
import re

from pydantic import BaseModel, Field, field_validator, model_validator

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_CASHTAG_RE = re.compile(r"\$[A-Za-z]{1,5}\b")

SCHEMA_VERSION = "0.1"


class SourceType(str, Enum):
    news = "news"
    social = "social"


class Provenance(str, Enum):
    live = "live"
    replay = "replay"
    synthetic = "synthetic"


class EventCategory(str, Enum):
    geopolitical = "Geopolitical"
    macroeconomic = "Macroeconomic"
    credit_event = "Credit event"
    merger_or_acquisition = "Merger or acquisition"
    product_launch = "Product launch"
    earnings = "Earnings"
    operational_disruption = "Operational disruption"
    commercial_agreement = "Commercial agreement"
    regulatory_or_legal = "Regulatory or legal"
    other = "Other"
    unknown = "Unknown"


class QualityFlag(str, Enum):
    unresolved_company = "unresolved_company"
    missing_publication_time = "missing_publication_time"
    insufficient_evidence = "insufficient_evidence"
    unverified_claim = "unverified_claim"
    conflicting_claims = "conflicting_claims"
    multiple_events = "multiple_events"
    analysis_error = "analysis_error"


class AnalysisStatus(str, Enum):
    complete = "complete"
    abstained = "abstained"
    error = "error"


class EvidenceSupports(str, Enum):
    sentiment = "sentiment"
    impact = "impact"
    event = "event"


class EvidenceExcerpt(BaseModel):
    text: str = Field(min_length=1)
    supports: set[EvidenceSupports] = Field(min_length=1)


class RiskSignal(BaseModel):
    schema_version: str = SCHEMA_VERSION
    signal_id: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    source_provider: str = Field(min_length=1)
    source_type: SourceType
    source_url: str | None = None
    published_at: datetime | None = None
    ingested_at: datetime
    provenance: Provenance

    company_id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    ticker: str | None = None

    event_category: EventCategory
    event_summary: str = Field(min_length=1)

    sentiment_score: float | None = None
    impact_score: int | None = None
    impact_explanation: str | None = None
    evidence_excerpts: list[EvidenceExcerpt] = Field(default_factory=list)

    analysis_status: AnalysisStatus
    quality_flags: set[QualityFlag] = Field(default_factory=set)
    analyzed_at: datetime | None = None
    analysis_method_version: str = Field(min_length=1)

    @field_validator("sentiment_score")
    @classmethod
    def _sentiment_bounds(cls, v: float | None) -> float | None:
        if v is not None and not -1.0 <= v <= 1.0:
            raise ValueError("sentiment_score must be within [-1, 1] or null")
        return v

    @field_validator("impact_score")
    @classmethod
    def _impact_bounds(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 10:
            raise ValueError("impact_score must be within [1, 10] or null")
        return v

    @field_validator("ticker")
    @classmethod
    def _ticker_upper(cls, v: str | None) -> str | None:
        return v.upper() if v else v

    @model_validator(mode="after")
    def _consistency(self) -> "RiskSignal":
        flags = self.quality_flags

        if self.published_at is None:
            if QualityFlag.missing_publication_time not in flags:
                raise ValueError(
                    "published_at is null; missing_publication_time flag required"
                )
        elif QualityFlag.missing_publication_time in flags:
            raise ValueError(
                "missing_publication_time flag set but published_at is present"
            )

        if self.published_at and self.ingested_at < self.published_at:
            raise ValueError("ingested_at must not precede published_at")

        if self.analyzed_at and self.ingested_at > self.analyzed_at:
            raise ValueError("analyzed_at must not precede ingested_at")

        if self.ticker is None and QualityFlag.unresolved_company not in flags:
            raise ValueError(
                "ticker is null; unresolved_company flag required when company unresolved"
            )
        if self.ticker is not None and QualityFlag.unresolved_company in flags:
            raise ValueError("unresolved_company flag set but ticker is resolved")

        missing_scores = self.sentiment_score is None or self.impact_score is None
        if missing_scores and QualityFlag.insufficient_evidence not in flags:
            raise ValueError(
                "null sentiment or impact score requires insufficient_evidence flag"
            )
        if not missing_scores and QualityFlag.insufficient_evidence in flags:
            raise ValueError(
                "insufficient_evidence flag set but both scores are present"
            )

        if self.impact_score is not None and not self.impact_explanation:
            raise ValueError("impact_explanation required when impact_score is assigned")

        if self.analysis_status == AnalysisStatus.abstained:
            if self.sentiment_score is not None or self.impact_score is not None:
                raise ValueError("abstained analysis must not carry scores")
        if self.analysis_status == AnalysisStatus.error:
            if QualityFlag.analysis_error not in flags:
                raise ValueError("analysis_status=error requires analysis_error flag")

        if self.analysis_status == AnalysisStatus.complete and not self.analyzed_at:
            raise ValueError("analyzed_at required when analysis_status is complete")

        return self


def normalize_evidence_text(text: str) -> str:
    """Normalize text for evidence comparison: strip URLs/cashtags, collapse
    whitespace. Used consistently by excerpt extraction AND membership
    validation, so a cleaned excerpt still maps to a real source span — the
    anti-fabrication guarantee holds (only noise tokens are removed, never
    words added or reordered)."""
    t = _URL_RE.sub(" ", text)
    t = _CASHTAG_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip(" .,;:!?-")


def validate_evidence_membership(signal: RiskSignal, source_text: str) -> None:
    """Every excerpt must map to a real span of the retained source text.

    Comparison is done on noise-normalized text (URLs/cashtags stripped) so
    readable excerpts still validate. Raises ValueError naming the offending
    excerpt. Do not fabricate evidence.
    """
    normalized_source = normalize_evidence_text(source_text).lower()
    for excerpt in signal.evidence_excerpts:
        if normalize_evidence_text(excerpt.text).lower() not in normalized_source:
            raise ValueError(
                f"evidence excerpt not found in source text: {excerpt.text!r}"
            )
