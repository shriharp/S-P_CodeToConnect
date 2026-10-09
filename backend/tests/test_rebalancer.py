from datetime import datetime, timedelta, timezone

from app.core.signal_contract import (
    AnalysisStatus,
    EventCategory,
    Provenance,
    QualityFlag,
    RiskSignal,
    SourceType,
)
from app.portfolio.rebalancer import MAX_WEIGHT, Portfolio, rebalance

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def make_signal(
    ticker="AAPL",
    sentiment=-1.0,
    ingested_at=NOW,
    status=AnalysisStatus.complete,
    company_id="acme",
    summary="Earnings missed estimates.",
    flags=None,
):
    return RiskSignal(
        signal_id=f"{ticker}-{sentiment}-{id(object())}",
        source_item_id="item",
        source_provider="test",
        source_type=SourceType.news,
        ingested_at=ingested_at,
        published_at=ingested_at,
        provenance=Provenance.synthetic,
        company_id=company_id,
        company_name=ticker,
        ticker=ticker,
        event_category=EventCategory.earnings,
        event_summary=summary,
        sentiment_score=sentiment,
        impact_score=None,
        impact_explanation=None,
        evidence_excerpts=[],
        analysis_status=status,
        quality_flags=flags or {QualityFlag.insufficient_evidence},
        analyzed_at=ingested_at,
        analysis_method_version="test",
    )


def portfolio():
    return Portfolio(
        weights={"AAPL": 0.2, "MSFT": 0.2, "JPM": 0.2, "XOM": 0.2, "PG": 0.2}
    )


def test_weights_sum_to_one():
    result = rebalance(portfolio(), [make_signal()], NOW)
    assert abs(sum(result.proposed_weights.values()) - 1.0) < 1e-9


def test_weights_nonnegative():
    result = rebalance(portfolio(), [make_signal(sentiment=-1.0)], NOW)
    assert min(result.proposed_weights.values()) >= 0


def test_cap_respected():
    p = Portfolio(
        weights={"AAPL": 0.6, "MSFT": 0.1, "JPM": 0.1, "XOM": 0.1, "PG": 0.1}
    )
    result = rebalance(p, [make_signal(sentiment=1.0)], NOW)
    assert result.proposed_weights["AAPL"] <= MAX_WEIGHT
    assert abs(sum(result.proposed_weights.values()) - 1.0) < 1e-9


def test_infeasible_caps_rejected():
    import pytest

    two = Portfolio(weights={"AAPL": 0.5, "MSFT": 0.5})
    with pytest.raises(ValueError, match="caps infeasible"):
        rebalance(two, [make_signal(sentiment=1.0)], NOW)


def test_direction_follows_sentiment():
    down = rebalance(portfolio(), [make_signal(sentiment=-1.0)], NOW)
    up = rebalance(portfolio(), [make_signal(sentiment=1.0)], NOW)
    assert down.adjustments["AAPL"] < 0
    assert up.adjustments["AAPL"] > 0


def test_stale_signal_skipped():
    stale = make_signal(ingested_at=NOW - timedelta(hours=72))
    result = rebalance(portfolio(), [stale], NOW)
    assert result.consumed_signal_ids == []
    assert result.skipped[0]["reason"] == "stale_or_future_ingested_at"


def test_duplicate_event_consumed_once():
    first = make_signal()
    second = make_signal()
    result = rebalance(portfolio(), [first, second], NOW)
    assert len(result.consumed_signal_ids) == 1
    assert result.skipped[0]["reason"] == "duplicate_event_already_consumed"


def test_incomplete_analysis_skipped():
    signal = make_signal(status=AnalysisStatus.abstained, sentiment=None)
    result = rebalance(portfolio(), [signal], NOW)
    assert result.consumed_signal_ids == []
    assert result.skipped[0]["reason"] == "analysis_not_complete"


def test_unknown_sentiment_skipped():
    signal = make_signal(sentiment=None)
    result = rebalance(portfolio(), [signal], NOW)
    assert result.skipped[0]["reason"] == "no_directional_sentiment"


def test_ticker_outside_portfolio_skipped():
    result = rebalance(portfolio(), [make_signal(ticker="TSLA")], NOW)
    assert result.skipped[0]["reason"] == "not_in_portfolio"


def test_portfolio_rejects_negative_weights():
    import pytest

    with pytest.raises(ValueError, match="nonnegative"):
        Portfolio(weights={"AAPL": -0.1, "MSFT": 1.1})
