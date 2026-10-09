from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.core.signal_contract import (
    AnalysisStatus,
    EventCategory,
    EvidenceExcerpt,
    EvidenceSupports,
    Provenance,
    QualityFlag,
    RiskSignal,
    SourceType,
    validate_evidence_membership,
)

SOURCE_TEXT = (
    "Acme Corp reported quarterly earnings that missed estimates. "
    "The company said a factory shutdown in June disrupted production "
    "and cut revenue by 8 percent."
)

BASE = {
    "signal_id": "sig-1",
    "source_item_id": "item-1",
    "source_provider": "test-wire",
    "source_type": SourceType.news,
    "ingested_at": datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
    "published_at": datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
    "provenance": Provenance.synthetic,
    "company_id": "acme",
    "company_name": "Acme Corp",
    "ticker": "ACME",
    "event_category": EventCategory.earnings,
    "event_summary": "Quarterly earnings missed estimates due to factory shutdown.",
    "sentiment_score": -0.6,
    "impact_score": 5,
    "impact_explanation": "Earnings miss with quantified revenue disruption.",
    "evidence_excerpts": [
        EvidenceExcerpt(text="missed estimates", supports={EvidenceSupports.sentiment}),
    ],
    "analysis_status": AnalysisStatus.complete,
    "quality_flags": set(),
    "analyzed_at": datetime(2026, 10, 1, 12, 5, tzinfo=timezone.utc),
    "analysis_method_version": "test-0",
}


def make(**overrides) -> RiskSignal:
    return RiskSignal(**{**BASE, **overrides})


def test_valid_signal_accepted():
    assert make().schema_version == "0.1"


@pytest.mark.parametrize("score", [-1.1, 1.1])
def test_sentiment_out_of_bounds_rejected(score):
    with pytest.raises(ValidationError, match="sentiment_score"):
        make(sentiment_score=score)


@pytest.mark.parametrize("score", [0, 11, -1])
def test_impact_out_of_bounds_rejected(score):
    with pytest.raises(ValidationError, match="impact_score"):
        make(impact_score=score)


def test_neutral_sentiment_is_zero_not_null():
    sig = make(sentiment_score=0.0)
    assert sig.sentiment_score == 0.0
    assert QualityFlag.insufficient_evidence not in sig.quality_flags


def test_null_sentiment_requires_flag():
    with pytest.raises(ValidationError, match="insufficient_evidence"):
        make(sentiment_score=None)


def test_null_scores_with_flag_and_abstained_accepted():
    sig = make(
        sentiment_score=None,
        impact_score=None,
        impact_explanation=None,
        quality_flags={QualityFlag.insufficient_evidence},
        analysis_status=AnalysisStatus.abstained,
        evidence_excerpts=[],
    )
    assert sig.sentiment_score is None
    assert sig.impact_score is None


def test_impact_without_explanation_rejected():
    with pytest.raises(ValidationError, match="impact_explanation"):
        make(impact_explanation=None)


def test_evidence_membership_valid():
    validate_evidence_membership(make(), SOURCE_TEXT)


def test_fabricated_evidence_rejected():
    sig = make(
        evidence_excerpts=[
            EvidenceExcerpt(text="revenue fell 40 percent", supports={EvidenceSupports.impact})
        ]
    )
    with pytest.raises(ValueError, match="not found in source text"):
        validate_evidence_membership(sig, SOURCE_TEXT)


def test_missing_publication_time_requires_flag():
    with pytest.raises(ValidationError, match="missing_publication_time"):
        make(published_at=None)


def test_ingested_before_published_rejected():
    with pytest.raises(ValidationError, match="ingested_at"):
        make(published_at=BASE["ingested_at"] + timedelta(hours=1))


def test_unresolved_company_requires_flag():
    with pytest.raises(ValidationError, match="unresolved_company"):
        make(ticker=None)


def test_abstained_cannot_carry_scores():
    with pytest.raises(ValidationError, match="abstained"):
        make(
            analysis_status=AnalysisStatus.abstained,
            quality_flags=set(),
        )


def test_error_status_requires_flag():
    with pytest.raises(ValidationError, match="analysis_error"):
        make(analysis_status=AnalysisStatus.error)


def test_company_results_independent():
    sig_a = make(signal_id="sig-a", company_id="acme", ticker="ACME")
    sig_b = make(
        signal_id="sig-b",
        company_id="globe",
        company_name="Globe Industries",
        ticker="GLBE",
        sentiment_score=0.4,
        impact_score=3,
    )
    assert sig_a.sentiment_score == -0.6
    assert sig_b.sentiment_score == 0.4
    assert sig_a.signal_id != sig_b.signal_id
