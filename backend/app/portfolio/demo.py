"""Mock index used for demonstrations (not an actual index).

Initial weights are seeded from real market caps (committed /data CSVs) when
available, so baseline allocation reflects genuine company scale. Falls back to
a documented static allocation when /data is absent — never fabricated.
"""

from datetime import datetime

from app.core.signal_contract import (
    AnalysisStatus,
    EventCategory,
    Provenance,
    QualityFlag,
    RiskSignal,
    SourceType,
)
from app.portfolio.rebalancer import Portfolio

# Static fallback weights (used only when /data/market CSVs are missing).
MOCK_INDEX = {
    "AAPL": 0.12,
    "MSFT": 0.12,
    "JPM": 0.10,
    "XOM": 0.10,
    "PG": 0.10,
    "KO": 0.10,
    "JNJ": 0.10,
    "WMT": 0.10,
    "CVX": 0.08,
    "PFE": 0.08,
}


def demo_portfolio() -> Portfolio:
    """Portfolio seeded from real market caps, capped to comply with policy.

    Market-cap weights are passed through the same bounded normalization the
    rebalancer uses, so the seed respects MAX_WEIGHT and no oversized opening
    position triggers an artificial first-rebalance correction. Relative
    market-cap ordering is preserved (largest company still largest weight).
    Falls back to a documented static allocation when /data is absent.
    """
    try:
        from app.market.loader import market_cap_weights
        from app.portfolio.rebalancer import MAX_WEIGHT, _bounded_normalize

        seeded = _bounded_normalize(market_cap_weights(), MAX_WEIGHT)
        return Portfolio(weights=seeded, name="demo-mock-index")
    except (FileNotFoundError, ValueError):
        # /data not populated (e.g. fresh clone before fetch) -> static fallback.
        return Portfolio(weights=dict(MOCK_INDEX), name="demo-mock-index")


def demo_signal(
    ticker: str,
    sentiment: float,
    text: str,
    source_item_id: str,
    ingested_at: datetime,
) -> RiskSignal:
    """Build a synthetic, clearly-labeled signal for demo/testing replay."""
    return RiskSignal(
        signal_id=f"{source_item_id}-{ticker}",
        source_item_id=source_item_id,
        source_provider="synthetic-fixture",
        source_type=SourceType.news,
        published_at=ingested_at,
        ingested_at=ingested_at,
        provenance=Provenance.synthetic,
        company_id=ticker.lower(),
        company_name=ticker,
        ticker=ticker,
        event_category=EventCategory.earnings,
        event_summary=text[:200],
        sentiment_score=sentiment,
        impact_score=None,
        impact_explanation=None,
        evidence_excerpts=[],
        analysis_status=AnalysisStatus.abstained
        if sentiment is None
        else AnalysisStatus.complete,
        quality_flags={QualityFlag.insufficient_evidence},
        analyzed_at=ingested_at,
        analysis_method_version="fixture-0.1",
    )
