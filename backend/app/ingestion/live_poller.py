"""Live ingestion orchestrator: poll free sources -> pipeline -> rebalancer.

The primary data path (AGENTS.md "Data Influx"): pulls live news (GDELT), live
social (StockTwits), and live quotes (yfinance), runs news/social through the
NLP pipeline, and feeds resulting signals into the rebalancer. Provenance=live.

Committed CSVs and the demo replay remain a labeled offline fallback only.
Every fetch is best-effort: a source that fails degrades gracefully (that source
contributes nothing this cycle) rather than fabricating data.
"""

from datetime import datetime, timezone

from app.core.signal_contract import Provenance
from app.ingestion.live_sources import (
    fetch_gdelt_news,
    fetch_index_symbols,
    fetch_live_quotes,
    fetch_stocktwits,
)
from app.nlp.pipeline import analyze_item
from app.portfolio.demo import demo_portfolio
from app.portfolio.rebalancer import Portfolio, RebalanceResult, rebalance

DEFAULT_NEWS_QUERY = "apple OR microsoft OR jpmorgan OR pfizer OR exxon"
SOCIAL_SYMBOLS = ("AAPL", "MSFT", "JPM")  # subset to keep poll weight low


def poll_live(
    portfolio: Portfolio | None = None,
    news_query: str = DEFAULT_NEWS_QUERY,
    sentiment_backend: str = "model",
    seen_source=None,
) -> dict:
    """One live ingestion cycle across all three free sources.

    seen_source: optional callable(source_item_id) -> bool. Items whose id has
    already been consumed (returns True) are skipped entirely, so repeated polls
    do NOT re-apply the same social/news item's adjustment (StockTwits returns
    identical recent messages every call). Without it, every poll re-drifts
    weights on stale posts.

    Returns {signals, decision_event, quotes, source_errors, skipped_seen}.
    Never raises on a single-source failure; records it in source_errors instead.
    """
    now = datetime.now(timezone.utc)
    portfolio = portfolio or demo_portfolio()
    signals = []
    source_errors: dict[str, str] = {}
    skipped_seen = 0

    def _keep_and_analyze(items):
        nonlocal skipped_seen
        out = []
        for item in items:
            if seen_source is not None and seen_source(item.external_id):
                skipped_seen += 1
                continue
            out.extend(
                analyze_item(item, provenance=Provenance.live.value,
                             sentiment_backend=sentiment_backend,
                             ingested_at=now)
            )
        return out

    # Live news (GDELT)
    try:
        signals.extend(_keep_and_analyze(fetch_gdelt_news(news_query, max_records=10)))
    except Exception as exc:  # degrade gracefully, never fabricate
        source_errors["news"] = f"{type(exc).__name__}: {exc}"

    # Live social (StockTwits) — one shared item per symbol's stream
    for sym in SOCIAL_SYMBOLS:
        try:
            signals.extend(_keep_and_analyze(fetch_stocktwits(sym, limit=10)))
        except Exception as exc:
            source_errors[f"social:{sym}"] = f"{type(exc).__name__}: {exc}"

    # Feed signals into the rebalancer (fresh signals only, at event time `now`).
    result: RebalanceResult = rebalance(portfolio, signals, now)

    # Live quotes (yfinance) — independent of the signal path, for price panels.
    try:
        quotes = fetch_live_quotes(fetch_index_symbols())
    except Exception as exc:
        quotes = {}
        source_errors["quotes"] = f"{type(exc).__name__}: {exc}"

    return {
        "signals": signals,
        "decision_event": result,
        "quotes": quotes,
        "source_errors": source_errors,
        "skipped_seen": skipped_seen,
        "polled_at": now.isoformat(),
    }
