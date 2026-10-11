from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.signal_contract import RiskSignal, SourceType
from app.ingestion.adapters import normalize_item
from app.ingestion.scheduler import IngestionScheduler
from app.ingestion.state import IngestionState
from app.ingestion.queue import RawItemQueue
from app.ingestion.events import hub
from app.nlp.pipeline import analyze, analyze_item
from app.portfolio.demo import demo_portfolio, demo_signal
from app.portfolio.rebalancer import RebalanceResult, rebalance
from app.replay import recorder
from app.replay.demo_sequence import replay as run_demo_replay, weight_timeline
from app.storage.ledger import RebalanceStore, SqliteRebalanceStore, event_from_result
from app.storage.signals import SignalStore, SqliteSignalStore

app = FastAPI(title="Risk Engine API", version="0.1.0")

RECORDINGS_DIR = Path(__file__).resolve().parents[2] / "recordings"
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "signals.db"
LEDGER_PATH = Path(__file__).resolve().parents[2] / "data" / "ledger.db"
INGESTION_STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "ingestion.db"
RAW_QUEUE_PATH = Path(__file__).resolve().parents[2] / "data" / "raw_items.db"

_store: SignalStore | None = None
_ledger: RebalanceStore | None = None
_ingestion_state: IngestionState | None = None
_scheduler: IngestionScheduler | None = None
_raw_queue: RawItemQueue | None = None


def get_store() -> SignalStore:
    global _store
    if _store is None:
        _store = SqliteSignalStore(DB_PATH)
    return _store


def get_ledger() -> RebalanceStore:
    global _ledger
    if _ledger is None:
        _ledger = SqliteRebalanceStore(LEDGER_PATH)
    return _ledger


def get_ingestion_state() -> IngestionState:
    global _ingestion_state
    if _ingestion_state is None:
        _ingestion_state = IngestionState(INGESTION_STATE_PATH)
        for provider, interval in (
            ("gdelt", 300), ("sec:edgar", 300), ("stocktwits", 30),
            ("reddit:r/stocks", 120), ("company:rss", 300), ("yfinance", 30)
        ):
            _ingestion_state.ensure_provider(provider, interval)
    return _ingestion_state


def get_raw_queue() -> RawItemQueue:
    global _raw_queue
    if _raw_queue is None:
        _raw_queue = RawItemQueue(RAW_QUEUE_PATH)
    return _raw_queue


def _run_scheduled_poll() -> None:
    # Scheduler persistence is deliberately routed through the same path as a
    # manual poll, so both modes share deduplication and ledger semantics.
    from app.ingestion.live_poller import poll_live

    state = get_ingestion_state()
    out = poll_live(news_query="apple OR microsoft OR jpmorgan OR pfizer OR exxon",
                   seen_source=get_store().has_source_item,
                   seen_item=lambda item: state.seen(item.provider, item.external_id),
                   record_item=lambda item, status: state.record_item(
                       item.provider, item.external_id, item.published_at, status
                   ),
                   raw_queue=get_raw_queue())
    for sig in out["signals"]:
        get_store().save(sig)
        state.record_item(sig.source_provider, sig.source_item_id, sig.published_at, "analyzed")
    event = out["decision_event"]
    event_id = f"scheduled-{out['polled_at'].replace(':', '').replace('.', '')}"
    get_ledger().append(event_from_result(event, event_id, datetime.fromisoformat(out["polled_at"])))
    hub.publish("poll", _live_event_payload(out, event_id, event))


def _live_event_payload(out: dict, event_id: str, event: RebalanceResult) -> dict:
    return {
        "event_id": event_id,
        "polled_at": out["polled_at"],
        "signals": [signal.model_dump(mode="json") for signal in out["signals"]],
        "source_counts": out.get("source_counts"),
        "source_errors": out.get("source_errors", {}),
        "skipped_seen": out.get("skipped_seen", 0),
        "decision_event": {
            "consumed_signal_ids": event.consumed_signal_ids,
            "decisions": [
                {"signal_id": decision.signal_id, "ticker": decision.ticker,
                 "decision": decision.decision, "reason": decision.reason}
                for decision in event.decisions
            ],
        },
    }


@app.on_event("startup")
def _start_scheduler() -> None:
    global _scheduler
    _scheduler = IngestionScheduler(_run_scheduled_poll)
    _scheduler.start()


@app.on_event("shutdown")
def _close_stores() -> None:
    global _store, _ledger, _ingestion_state, _scheduler, _raw_queue
    if _scheduler is not None:
        _scheduler.stop()
    if _store is not None:
        _store.close()
        _store = None
    if _ledger is not None:
        _ledger.close()
        _ledger = None
    if _ingestion_state is not None:
        _ingestion_state.close()
        _ingestion_state = None
    if _raw_queue is not None:
        _raw_queue.close()
        _raw_queue = None


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    source_provider: str = "unknown"
    provenance: str = "live"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0", "scheduler_enabled": bool(_scheduler and _scheduler.enabled)}


@app.get("/live/health")
def live_health(state: IngestionState = Depends(get_ingestion_state)) -> dict:
    return {
        "scheduler_enabled": bool(_scheduler and _scheduler.enabled),
        "providers": state.health(),
        "queue": get_raw_queue().counts(),
    }


@app.get("/live/providers/{provider:path}/items")
def live_provider_items(
    provider: str,
    search: str = "",
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
    state: IngestionState = Depends(get_ingestion_state),
    queue: RawItemQueue = Depends(get_raw_queue),
    store: SignalStore = Depends(get_store),
) -> dict:
    """Inspect durable source and raw-queue records for one provider."""
    queue_items = queue.list_items(
        provider, search=search, status=status, limit=limit, offset=offset
    )
    for item in queue_items:
        import json
        item["payload"] = json.loads(item["payload"])
        item["analysis"] = [
            signal.model_dump()
            for signal in store.list(limit=500)
            if signal.source_provider == provider
            and signal.source_item_id == item["external_id"]
        ]
    source_items = state.list_source_items(
        provider, search=search, limit=limit, offset=offset
    )
    return {
        "provider": provider,
        "items": queue_items,
        "source_items": source_items,
        "total": queue.count_items(provider, search=search, status=status),
        "limit": min(limit, 100),
        "offset": max(offset, 0),
    }


@app.get("/live/events")
async def live_events() -> StreamingResponse:
    async def stream():
        yield ": connected\n\n"
        async for event in hub.subscribe():
            yield event.encode()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/analyze", response_model=RiskSignal)
def analyze_text(req: AnalyzeRequest) -> RiskSignal:
    try:
        return analyze(
            req.text,
            source_item_id=req.source_item_id,
            provider=req.source_provider,
            provenance=req.provenance,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class IngestItem(BaseModel):
    id: str = Field(min_length=1)
    headline: str | None = None
    text: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    provider: str | None = None


class IngestRequest(BaseModel):
    source_type: SourceType
    items: list[IngestItem] = Field(min_length=1)
    provenance: str = "live"
    record: bool = False
    sentiment_backend: str = "model"
    event_backend: str = "finetuned"


@app.post("/ingest", response_model=list[RiskSignal])
def ingest(req: IngestRequest, store: SignalStore = Depends(get_store)) -> list[RiskSignal]:
    """Normalize and analyze a batch of news or social items; persist results."""
    if req.provenance not in ("live", "replay", "synthetic"):
        raise HTTPException(status_code=422, detail="invalid provenance")
    if req.sentiment_backend not in ("lexicon", "model"):
        raise HTTPException(status_code=422, detail="invalid sentiment_backend")
    if req.event_backend not in ("keyword", "model", "hybrid", "finetuned"):
        raise HTTPException(status_code=422, detail="invalid event_backend")
    signals: list[RiskSignal] = []
    for raw in req.items:
        payload = raw.model_dump(exclude_none=True)
        try:
            item = normalize_item(req.source_type, payload)
            signals.extend(
                analyze_item(
                    item,
                    provenance=req.provenance,
                    sentiment_backend=req.sentiment_backend,
                    event_backend=req.event_backend,
                )
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=422, detail=f"item {raw.id}: {exc}"
            ) from exc
    for signal in signals:
        store.save(signal)
    if req.record:
        RECORDINGS_DIR.mkdir(exist_ok=True)
        path = RECORDINGS_DIR / f"ingest-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.jsonl"
        for signal in signals:
            recorder.record(signal, path)
    return signals


class ReplayRequest(BaseModel):
    file: str = Field(min_length=1)


@app.get("/signals", response_model=list[RiskSignal])
def list_signals(
    ticker: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
    dashboard: str = "all",
    store: SignalStore = Depends(get_store),
) -> list[RiskSignal]:
    """Query persisted signals (newest first).

    Dashboard views use an explicit scope so strategy-lab experiments, test
    fixtures, and recorded demo data do not leak into live mode.
    """
    signals = store.list(ticker=ticker, since=since, limit=500)
    if dashboard == "demo":
        signals = [s for s in signals if s.provenance.value == "replay"]
    elif dashboard == "live":
        signals = [
            s for s in signals
            if s.provenance.value == "live"
            and s.source_provider not in {"strategy-lab", "test"}
        ]
    elif dashboard != "all":
        raise HTTPException(status_code=422, detail="invalid dashboard scope")
    return signals[: min(limit, 500)]


@app.get("/signals/count")
def signals_count(store: SignalStore = Depends(get_store)) -> dict:
    return {"count": store.count()}


@app.get("/signals/overview")
def signals_overview(dashboard: str = "all", store: SignalStore = Depends(get_store)) -> dict:
    """Aggregate distributions over persisted signals (Market Risk Overview).

    Descriptive counts only, computed from real stored signals — no fabricated
    metrics. Nulls are counted, never imputed.
    """
    signals = list_signals(dashboard=dashboard, store=store)
    n = len(signals)
    event_counts: dict[str, int] = {}
    provenance_counts: dict[str, int] = {}
    impact_counts: dict[str, int] = {}
    senti_vals: list[float] = []
    impact_vals: list[int] = []
    null_sentiment = 0
    null_impact = 0
    for s in signals:
        # Chatter grouping (matches frontend display rule): a social post with no
        # distinct event but scored sentiment is chatter, not a bare "Unknown".
        if (
            s.source_type.value == "social"
            and s.event_category.value == "Unknown"
            and s.sentiment_score is not None
        ):
            cat = "Social chatter"
        else:
            cat = s.event_category.value
        event_counts[cat] = event_counts.get(cat, 0) + 1
        provenance_counts[s.provenance.value] = provenance_counts.get(s.provenance.value, 0) + 1
        if s.sentiment_score is None:
            null_sentiment += 1
        else:
            senti_vals.append(s.sentiment_score)
        if s.impact_score is None:
            null_impact += 1
        else:
            impact_vals.append(s.impact_score)
            impact_counts[str(s.impact_score)] = impact_counts.get(str(s.impact_score), 0) + 1
    return {
        "total": n,
        "event_counts": dict(sorted(event_counts.items(), key=lambda kv: -kv[1])),
        "provenance_counts": provenance_counts,
        "impact_counts": dict(sorted(impact_counts.items(), key=lambda kv: int(kv[0]))),
        "sentiment": {
            "scored": len(senti_vals),
            "null": null_sentiment,
            "mean": round(sum(senti_vals) / len(senti_vals), 4) if senti_vals else None,
            "positive": sum(1 for v in senti_vals if v > 0),
            "negative": sum(1 for v in senti_vals if v < 0),
            "neutral": sum(1 for v in senti_vals if v == 0),
        },
        "impact": {
            "scored": len(impact_vals),
            "null": null_impact,
            "mean": round(sum(impact_vals) / len(impact_vals), 2) if impact_vals else None,
        },
    }


@app.post("/replay", response_model=list[RiskSignal])
def replay(req: ReplayRequest) -> list[RiskSignal]:
    """Serve recorded signals without running inference (mode: recorded replay)."""
    name = Path(req.file).name  # path-traversal guard: flat filenames only
    path = RECORDINGS_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"recording not found: {name}")
    try:
        return recorder.load(path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class RebalanceItem(BaseModel):
    ticker: str
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    text: str = Field(min_length=1)
    source_item_id: str


class RebalanceRequest(BaseModel):
    items: list[RebalanceItem] = Field(min_length=1)


class SimulateTextRequest(BaseModel):
    text: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    source_type: SourceType = SourceType.news
    provenance: str = "live"


@app.post("/rebalance", response_model=RebalanceResult)
def rebalance_portfolio(
    req: RebalanceRequest, ledger: RebalanceStore = Depends(get_ledger)
) -> RebalanceResult:
    """Propose mock-index weights after consuming the supplied signals.

    Persists an auditable decision-ledger event. Signals are synthetic fixtures
    (provenance=synthetic); live signals arrive through /analyze + /ingest.
    """
    now = datetime.now(timezone.utc)
    signals = [
        demo_signal(
            ticker=item.ticker.upper(),
            sentiment=item.sentiment_score,
            text=item.text,
            source_item_id=item.source_item_id,
            ingested_at=now,
        )
        for item in req.items
    ]
    result = rebalance(demo_portfolio(), signals, now)
    event_id = f"rb-{now:%Y%m%dT%H%M%S%fZ}"
    ledger.append(event_from_result(result, event_id, now))
    return result


@app.post("/simulate", response_model=RebalanceResult)
def simulate(req: RebalanceRequest) -> RebalanceResult:
    """Read-only what-if simulation: real rebalancer logic, NO persistence.

    Runs the same policy engine as /rebalance (caps, gates, renormalization) but
    writes nothing to the ledger or weight-history, so experiments never mutate
    the audited demo portfolio state. Non-persistent by design.
    """
    now = datetime.now(timezone.utc)
    signals = [
        demo_signal(
            ticker=item.ticker.upper(),
            sentiment=item.sentiment_score,
            text=item.text,
            source_item_id=item.source_item_id,
            ingested_at=now,
        )
        for item in req.items
    ]
    return rebalance(demo_portfolio(), signals, now)


@app.post("/simulate-text")
def simulate_text(req: SimulateTextRequest) -> dict:
    """Analyze text and immediately run a non-persistent counterfactual.

    This keeps article interpretation and portfolio what-if analysis in one
    workflow without saving ad-hoc input to the live signal feed or ledger.
    """
    if req.provenance not in ("live", "replay", "synthetic"):
        raise HTTPException(status_code=422, detail="invalid provenance")
    item = normalize_item(
        req.source_type,
        {"id": req.source_item_id, "text": req.text, "provider": "strategy-lab"},
    )
    signals = analyze_item(item, provenance=req.provenance)
    now = datetime.now(timezone.utc)
    eligible = [
        demo_signal(
            ticker=s.ticker,
            sentiment=s.sentiment_score,
            text=s.event_summary,
            source_item_id=s.source_item_id,
            ingested_at=now,
        )
        for s in signals
        if s.ticker and s.sentiment_score not in (None, 0)
    ]
    result = rebalance(demo_portfolio(), eligible, now)
    return {"signals": [s.model_dump() for s in signals], "result": result}


@app.get("/ledger", response_model=list[dict])
def list_ledger(
    limit: int = 100, dashboard: str = "all",
    ledger: RebalanceStore = Depends(get_ledger)
) -> list[dict]:
    """Rebalance decision ledger, newest first (audit view)."""
    from dataclasses import asdict

    events = ledger.list_events(limit=500)
    if dashboard == "demo":
        events = [e for e in events if e.event_id.startswith("demo-")]
    elif dashboard == "live":
        events = [
            e for e in events
            if e.event_id.startswith(("live-", "scheduled-"))
        ]
    elif dashboard != "all":
        raise HTTPException(status_code=422, detail="invalid dashboard scope")
    return [
        {**asdict(e), "timestamp": e.timestamp.isoformat()}
        for e in events[: min(limit, 500)]
    ]


@app.get("/portfolio/weight-history")
def weight_history(
    dashboard: str = "all", ledger: RebalanceStore = Depends(get_ledger)
) -> list[dict]:
    """Chronological per-ticker weight series for the evolution timeline."""
    events = list_ledger(dashboard=dashboard, limit=500, ledger=ledger)
    return [
        {
            "event_id": event["event_id"],
            "timestamp": event["timestamp"],
            "weights": event["final_weights"],
        }
        for event in reversed(events)
    ]


@app.get("/portfolio/performance")
def portfolio_performance(
    dashboard: str = "all",
    ledger: RebalanceStore = Depends(get_ledger),
) -> dict:
    """Descriptive performance metrics vs equal-weight / buy-and-hold baselines.

    Strictly descriptive (not a predictive backtest) — computed from real price
    history + recorded weights, no look-ahead, nulls never fabricated.
    """
    from app.portfolio.performance import compute_performance

    return compute_performance(weight_history(dashboard=dashboard, ledger=ledger))


@app.get("/benchmark/sentiment")
def benchmark_sentiment(refresh: bool = False) -> dict:
    """Measured lexicon-vs-model sentiment benchmark (P1.5).

    Runs on the labeled dev fixtures; returns accuracy, confusion matrix,
    per-class recall, and latency for each backend. Measured, cached — never
    hardcoded. Fixtures are synthetic dev labels, NOT a real-world accuracy
    claim. Model metrics are None (with a reason) if transformers is absent.
    """
    from benchmarks.sentiment_benchmark import run_benchmark

    return run_benchmark(force_refresh=refresh)


@app.get("/market/prices")
def market_prices(tickers: str | None = None) -> dict:
    """Real close-price history from committed /data CSVs (offline, no network).

    Returns {ticker: {date: close}}. Optional comma-separated `tickers` filter.
    """
    from app.market.loader import load_prices

    try:
        prices = load_prices()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if tickers:
        wanted = {t.strip().upper() for t in tickers.split(",") if t.strip()}
        prices = {t: s for t, s in prices.items() if t in wanted}
    return {t: {d.isoformat(): v for d, v in series.items()} for t, series in prices.items()}


@app.get("/market/sectors")
def market_sectors() -> dict:
    """Sector + market-cap metadata per ticker (for exposure heatmap + seeding)."""
    from app.market.loader import load_metadata

    try:
        metas = load_metadata()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        m.ticker: {"company_id": m.company_id, "sector": m.sector, "market_cap": m.market_cap}
        for m in metas
    }


@app.post("/demo/replay", response_model=list[dict])
def demo_replay(
    ledger: RebalanceStore = Depends(get_ledger),
    store: SignalStore = Depends(get_store),
) -> list[dict]:
    """Run the committed deterministic demo sequence offline.

    Replays data/demo_news.jsonl through the real pipeline + rebalancer,
    persisting each step's signals and decision event to the ledger. This is the
    reproducible demo backbone: no network, no live inference timing.
    """
    from datetime import datetime

    steps = run_demo_replay()
    out: list[dict] = []
    for i, step in enumerate(steps):
        signals = step["signals"]
        event = step["decision_event"]
        for sig in signals:
            store.save(sig)
        ts = datetime.fromisoformat(step["published_at"].replace("Z", "+00:00"))
        event_id = f"demo-{i:02d}-{step['item_id']}"
        ledger.append(event_from_result(event, event_id, ts))
        out.append(
            {
                "item_id": step["item_id"],
                "published_at": step["published_at"],
                "event_id": event_id,
                "signals": [s.model_dump() for s in signals],
                "final_weights": event.proposed_weights,
                "consumed_signal_ids": event.consumed_signal_ids,
                "decisions": [
                    {
                        "signal_id": d.signal_id,
                        "ticker": d.ticker,
                        "decision": d.decision,
                        "reason": d.reason,
                        "final_weight": d.final_weight,
                    }
                    for d in event.decisions
                ],
            }
        )
    return out


@app.post("/live/poll", response_model=dict)
def live_poll(
    news_query: str = "apple OR microsoft OR jpmorgan OR pfizer OR exxon",
    ledger: RebalanceStore = Depends(get_ledger),
    store: SignalStore = Depends(get_store),
    state: IngestionState = Depends(get_ingestion_state),
) -> dict:
    """One live ingestion cycle: GDELT news + StockTwits social + yfinance quotes.

    Primary data path (provenance=live). Persists signals + the rebalance event
    to the ledger. A source that fails degrades gracefully and is reported in
    source_errors; never silently substituted with fabricated data.
    """
    from app.ingestion.live_poller import poll_live

    out = poll_live(
        news_query=news_query,
        seen_source=store.has_source_item,
        seen_item=lambda item: state.seen(item.provider, item.external_id),
        record_item=lambda item, status: state.record_item(
            item.provider, item.external_id, item.published_at, status
        ),
        raw_queue=get_raw_queue(),
    )
    event = out["decision_event"]
    for sig in out["signals"]:
        store.save(sig)
        state.record_item(sig.source_provider, sig.source_item_id, sig.published_at, "analyzed")
    fetched = out.get("source_counts", {}).get("fetched", {})
    analyzed = out.get("source_counts", {}).get("analyzed", {})
    provider_map = {
        "gdelt_news": "gdelt",
        "sec_edgar": "sec:edgar",
        "company_rss": "company:rss",
        "stocktwits": "stocktwits",
        "reddit": "reddit:r/stocks",
    }
    for key, provider in provider_map.items():
        provider_error = (
            out.get("source_errors", {}).get("news")
            if key == "gdelt_news"
            else next(
                (
                    message
                    for name, message in out.get("source_errors", {}).items()
                    if name.startswith("sec:")
                ),
                None,
            )
            if key == "sec_edgar"
            else next(
                (
                    message
                    for name, message in out.get("source_errors", {}).items()
                    if name.startswith("rss:")
                ),
                None,
            )
            if key == "company_rss"
            else out.get("source_errors", {}).get(f"social:{provider.split(':')[0]}")
        )
        state.update_provider(
            provider,
            attempted=True,
            success=provider_error is None or fetched.get(key, 0) > 0,
            fetched=fetched.get(key, 0),
            analyzed=analyzed.get(key, 0),
            skipped=out.get("skipped_seen", 0) if key == "stocktwits" else 0,
            error=provider_error,
        )
    state.update_provider(
        "yfinance",
        attempted=True,
        success="quotes" not in out.get("source_errors", {}),
        fetched=len(out.get("quotes", {})),
        error=out.get("source_errors", {}).get("quotes"),
    )
    event_id = f"live-{out['polled_at'].replace(':', '').replace('.', '')}"
    ledger.append(event_from_result(event, event_id, datetime.fromisoformat(out["polled_at"])))
    hub.publish("poll", _live_event_payload(out, event_id, event))

    out["signals"] = [s.model_dump() for s in out["signals"]]
    out["event_id"] = event_id
    out["decision_event"] = {
        "proposed_weights": event.proposed_weights,
        "original_weights": event.original_weights,
        "adjustments": event.adjustments,
        "consumed_signal_ids": event.consumed_signal_ids,
        "decisions": [
            {
                "signal_id": d.signal_id,
                "ticker": d.ticker,
                "decision": d.decision,
                "reason": d.reason,
                "original_weight": d.original_weight,
                "final_weight": d.final_weight,
            }
            for d in event.decisions
        ],
        "policy_version": event.policy_version,
        "disclaimer": event.disclaimer,
    }
    return out
