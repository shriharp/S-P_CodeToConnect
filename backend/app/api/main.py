from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.signal_contract import RiskSignal
from app.nlp.pipeline import analyze
from app.portfolio.demo import demo_portfolio, demo_signal
from app.portfolio.rebalancer import RebalanceResult, rebalance

app = FastAPI(title="Risk Engine API", version="0.1.0")


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
