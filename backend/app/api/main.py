from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.signal_contract import RiskSignal, SourceType
from app.ingestion.adapters import normalize_item
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

_store: SignalStore | None = None
_ledger: RebalanceStore | None = None


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


@app.on_event("shutdown")
def _close_stores() -> None:
    global _store, _ledger
    if _store is not None:
        _store.close()
        _store = None
    if _ledger is not None:
        _ledger.close()
        _ledger = None


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    source_provider: str = "unknown"
    provenance: str = "live"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


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
    sentiment_backend: str = "lexicon"


@app.post("/ingest", response_model=list[RiskSignal])
def ingest(req: IngestRequest, store: SignalStore = Depends(get_store)) -> list[RiskSignal]:
    """Normalize and analyze a batch of news or social items; persist results."""
    if req.provenance not in ("live", "replay", "synthetic"):
        raise HTTPException(status_code=422, detail="invalid provenance")
    if req.sentiment_backend not in ("lexicon", "model"):
        raise HTTPException(status_code=422, detail="invalid sentiment_backend")
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
    store: SignalStore = Depends(get_store),
) -> list[RiskSignal]:
    """Query persisted signals (newest first)."""
    return store.list(ticker=ticker, since=since, limit=min(limit, 500))


@app.get("/signals/count")
def signals_count(store: SignalStore = Depends(get_store)) -> dict:
    return {"count": store.count()}


@app.get("/signals/overview")
def signals_overview(store: SignalStore = Depends(get_store)) -> dict:
    """Aggregate distributions over persisted signals (Market Risk Overview).

    Descriptive counts only, computed from real stored signals — no fabricated
    metrics. Nulls are counted, never imputed.
    """
    signals = store.list(limit=500)
    n = len(signals)
    event_counts: dict[str, int] = {}
    provenance_counts: dict[str, int] = {}
    impact_counts: dict[str, int] = {}
    senti_vals: list[float] = []
    impact_vals: list[int] = []
    null_sentiment = 0
    null_impact = 0
    for s in signals:
        event_counts[s.event_category.value] = event_counts.get(s.event_category.value, 0) + 1
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


@app.get("/ledger", response_model=list[dict])
def list_ledger(
    limit: int = 100, ledger: RebalanceStore = Depends(get_ledger)
) -> list[dict]:
    """Rebalance decision ledger, newest first (audit view)."""
    from dataclasses import asdict

    return [
        {**asdict(e), "timestamp": e.timestamp.isoformat()}
        for e in ledger.list_events(limit=min(limit, 500))
    ]


@app.get("/portfolio/weight-history")
def weight_history(ledger: RebalanceStore = Depends(get_ledger)) -> list[dict]:
    """Chronological per-ticker weight series for the evolution timeline."""
    return ledger.weight_history()


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
) -> dict:
    """One live ingestion cycle: GDELT news + StockTwits social + yfinance quotes.

    Primary data path (provenance=live). Persists signals + the rebalance event
    to the ledger. A source that fails degrades gracefully and is reported in
    source_errors; never silently substituted with fabricated data.
    """
    from app.ingestion.live_poller import poll_live

    out = poll_live(news_query=news_query, seen_source=store.has_source_item)
    event = out["decision_event"]
    for sig in out["signals"]:
        store.save(sig)
    event_id = f"live-{out['polled_at'].replace(':', '').replace('.', '')}"
    ledger.append(event_from_result(event, event_id, datetime.fromisoformat(out["polled_at"])))

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
