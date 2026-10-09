from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.signal_contract import RiskSignal
from app.nlp.pipeline import analyze

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
