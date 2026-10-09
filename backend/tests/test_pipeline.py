from app.core.signal_contract import (
    AnalysisStatus,
    EventCategory,
    QualityFlag,
    SourceType,
)
from app.ingestion.adapters import RawSourceItem
from app.nlp.pipeline import analyze, analyze_item


def news_item(text, external_id="t-1", published_at=None):
    return RawSourceItem(
        provider="test",
        source_type=SourceType.news,
        external_id=external_id,
        text=text,
        published_at=published_at,
    )


def test_negative_news_produces_negative_signal():
    sig = analyze(
        "Acme cut revenue by 8 percent after a factory shutdown.",
        source_item_id="t-1",
        provider="test",
        provenance="synthetic",
    )
    assert sig.sentiment_score is not None and sig.sentiment_score < 0
    assert sig.impact_score is not None
    assert sig.event_category is not EventCategory.unknown


def test_evidence_excerpts_are_substrings():
    text = "Acme cut revenue by 8 percent after a factory shutdown."
    sig = analyze(text, source_item_id="t-1", provider="test", provenance="synthetic")
    for excerpt in sig.evidence_excerpts:
        assert excerpt.text in text


def test_no_cues_abstains():
    sig = analyze(
        "The meeting is on Tuesday.",
        source_item_id="t-2",
        provider="test",
        provenance="synthetic",
    )
    assert sig.analysis_status is AnalysisStatus.abstained
    assert sig.sentiment_score is None
    assert sig.impact_score is None
    assert QualityFlag.insufficient_evidence in sig.quality_flags


def test_missing_published_at_flagged():
    sig = analyze_item(
        news_item("Acme wins a contract partnership."), provenance="live"
    )[0]
    assert QualityFlag.missing_publication_time in sig.quality_flags
    assert sig.published_at is None


def test_social_source_type_preserved():
    item = RawSourceItem(
        provider="social-adapter",
        source_type=SourceType.social,
        external_id="so-1",
        text="AAPL plunge after lawsuit, downgrade fears!",
    )
    sig = analyze_item(item, provenance="synthetic")[0]
    assert sig.source_type is SourceType.social


def test_resolved_company_carries_ticker():
    sig = analyze_item(news_item("Apple wins a contract."), provenance="live")[0]
    assert sig.ticker == "AAPL"
    assert QualityFlag.unresolved_company not in sig.quality_flags


def test_multi_company_text_produces_one_signal_each():
    signals = analyze_item(
        news_item("Apple cut revenue while Pfizer won a partnership contract."),
        provenance="live",
    )
    assert {s.ticker for s in signals} == {"AAPL", "PFE"}
    assert len({s.signal_id for s in signals}) == 2


def test_unresolved_company_flagged():
    sig = analyze_item(
        news_item("Some unknown firm won a contract."), provenance="live"
    )[0]
    assert sig.ticker is None
    assert QualityFlag.unresolved_company in sig.quality_flags
