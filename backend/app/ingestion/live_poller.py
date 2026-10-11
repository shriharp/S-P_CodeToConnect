"""Live ingestion orchestrator: poll free sources -> pipeline -> rebalancer.

The primary data path (AGENTS.md "Data Influx"): pulls live news (GDELT), live
social (StockTwits), and live quotes (yfinance), runs news/social through the
NLP pipeline, and feeds resulting signals into the rebalancer. Provenance=live.

Committed CSVs and the demo replay remain a labeled offline fallback only.
Every fetch is best-effort: a source that fails degrades gracefully (that source
contributes nothing this cycle) rather than fabricating data.
"""

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.signal_contract import Provenance
from app.ingestion.live_sources import (
    fetch_gdelt_news,
    fetch_index_symbols,
    fetch_live_quotes,
    fetch_reddit_rss,
    fetch_sec_filings,
    fetch_stocktwits,
)
from app.nlp.pipeline import analyze_item
from app.portfolio.demo import demo_portfolio
from app.portfolio.rebalancer import Portfolio, RebalanceResult, rebalance

DEFAULT_NEWS_QUERY = "apple OR microsoft OR jpmorgan OR pfizer OR exxon"
SOCIAL_SYMBOLS = ("AAPL", "MSFT", "JPM", "XOM", "PG", "KO", "JNJ", "WMT", "CVX", "PFE")
REDDIT_QUERY = "Apple OR Microsoft OR JPMorgan OR Exxon OR Procter Gamble OR Coca-Cola OR Johnson Johnson OR Walmart OR Chevron OR Pfizer"


def poll_live(
    portfolio: Portfolio | None = None,
    news_query: str = DEFAULT_NEWS_QUERY,
    sentiment_backend: str = "model",
    event_backend: str = "hybrid",
    seen_source=None,
    seen_item=None,
    record_item=None,
    raw_queue=None,
    queue_batch_size: int = 100,
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
    fetched_counts = {"gdelt_news": 0, "sec_edgar": 0, "stocktwits": 0, "reddit": 0}

    def _keep_and_analyze(items):
        nonlocal skipped_seen
        out = []
        for item in items:
            if (
                (seen_source is not None and seen_source(item.external_id))
                or (seen_item is not None and seen_item(item))
            ):
                skipped_seen += 1
                continue
            if record_item is not None:
                record_item(item, "fetched")
            if raw_queue is not None:
                raw_queue.enqueue(item)
            else:
                out.extend(
                    analyze_item(item, provenance=Provenance.live.value,
                                 sentiment_backend=sentiment_backend,
                                 event_backend=event_backend,
                                 ingested_at=now)
                )
        return out

    # Live news (GDELT)
    try:
        items = fetch_gdelt_news(news_query, max_records=10)
        fetched_counts["gdelt_news"] = len(items)
        signals.extend(_keep_and_analyze(items))
    except Exception as exc:  # degrade gracefully, never fabricate
        source_errors["news"] = f"{type(exc).__name__}: {exc}"

    # SEC EDGAR metadata is an additive authoritative filing signal.
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_sec_filings, symbol, 5): symbol
            for symbol in SOCIAL_SYMBOLS
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                items = future.result()
                fetched_counts["sec_edgar"] += len(items)
                signals.extend(_keep_and_analyze(items))
            except Exception as exc:
                source_errors[f"sec:{symbol}"] = f"{type(exc).__name__}: {exc}"

    # Live social (StockTwits) — one shared item per symbol's stream.
    # labeled_only keeps just posts StockTwits self-labeled Bullish/Bearish,
    # cutting the ticker-spam noise that otherwise floods as Unknown/neutral.
    # These requests are independent. Fetching them concurrently avoids making
    # users wait for ten sequential network timeouts while preserving the
    # existing per-symbol error reporting.
    with ThreadPoolExecutor(max_workers=len(SOCIAL_SYMBOLS)) as executor:
        futures = {
            executor.submit(fetch_stocktwits, sym, 25, True): sym
            for sym in SOCIAL_SYMBOLS
        }
        for future in as_completed(futures):
            sym = futures[future]
            try:
                items = future.result()
                fetched_counts["stocktwits"] += len(items)
                signals.extend(_keep_and_analyze(items))
            except Exception as exc:
                source_errors[f"social:{sym}"] = f"{type(exc).__name__}: {exc}"

    # Public Reddit RSS is optional enrichment. It has no native sentiment
    # label, so sentiment remains an NLP inference with normal quality rules.
    try:
        items = fetch_reddit_rss(REDDIT_QUERY, limit=25)
        fetched_counts["reddit"] = len(items)
        signals.extend(_keep_and_analyze(items))
    except Exception as exc:
        source_errors["social:reddit"] = f"{type(exc).__name__}: {exc}"

    if raw_queue is not None:
        for rowid, item in raw_queue.claim(queue_batch_size):
            try:
                signals.extend(
                    analyze_item(item, provenance=Provenance.live.value,
                                 sentiment_backend=sentiment_backend,
                                 event_backend=event_backend,
                                 ingested_at=now)
                )
                raw_queue.complete(rowid)
            except Exception as exc:
                raw_queue.fail(rowid, f"{type(exc).__name__}: {exc}")
                source_errors[f"queue:{item.provider}"] = str(exc)

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
        "source_counts": {
            "fetched": fetched_counts,
            "analyzed": {
                "gdelt_news": sum(1 for s in signals if s.source_provider == "gdelt"),
                "sec_edgar": sum(1 for s in signals if s.source_provider == "sec:edgar"),
                "stocktwits": sum(1 for s in signals if s.source_provider.startswith("stocktwits:")),
                "reddit": sum(1 for s in signals if s.source_provider == "reddit:r/stocks"),
            },
            "quotes": len(quotes),
            "queue": raw_queue.counts() if raw_queue is not None else None,
        },
        "polled_at": now.isoformat(),
    }
