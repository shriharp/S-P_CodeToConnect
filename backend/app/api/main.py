from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.signal_contract import RiskSignal, SourceType
from app.ingestion.adapters import normalize_item
from app.nlp.pipeline import analyze, analyze_item
from app.portfolio.demo import demo_portfolio, demo_signal
from app.portfolio.rebalancer import RebalanceResult, rebalance
from app.replay import recorder

app = FastAPI(title="Risk Engine API", version="0.1.0")

RECORDINGS_DIR = Path(__file__).resolve().parents[2] / "recordings"


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


@app.post("/ingest", response_model=list[RiskSignal])
def ingest(req: IngestRequest) -> list[RiskSignal]:
    """Normalize and analyze a batch of news or social items."""
    if req.provenance not in ("live", "replay", "synthetic"):
        raise HTTPException(status_code=422, detail="invalid provenance")
    signals: list[RiskSignal] = []
    for raw in req.items:
        payload = raw.model_dump(exclude_none=True)
        try:
            item = normalize_item(req.source_type, payload)
            signal = analyze_item(item, provenance=req.provenance)
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=422, detail=f"item {raw.id}: {exc}"
            ) from exc
        signals.append(signal)
    if req.record:
        RECORDINGS_DIR.mkdir(exist_ok=True)
        path = RECORDINGS_DIR / f"ingest-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.jsonl"
        for signal in signals:
            recorder.record(signal, path)
    return signals


class ReplayRequest(BaseModel):
    file: str = Field(min_length=1)


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
def rebalance_portfolio(req: RebalanceRequest) -> RebalanceResult:
    """Propose mock-index weights after consuming the supplied signals.

    Signals are synthetic fixtures (provenance=synthetic) until ingestion
    lands; live signals arrive through /analyze.
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
