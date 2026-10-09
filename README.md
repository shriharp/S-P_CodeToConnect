# Risk Engine

Submission for S&P Global and CRISIL's Code to Connect 2026 hackathon.

An AI/NLP financial risk engine: financial news and social text become
company-specific, explainable risk signals, which drive a transparent mock-index
rebalancing demo (Module A).

## Pipeline

1. Normalize text and source metadata (news or social adapters).
2. Classify the primary event and company-specific sentiment (lightweight NLP).
3. Score financial impact deterministically, with abstention when evidence is
   insufficient (null, never a fabricated score).
4. Validate against the signal contract (bounds, null-versus-neutral, evidence
   membership, timestamps, quality-flag consistency).
5. Apply Module A's portfolio policy: sentiment-direction adjustments, position
  caps, freshness and duplicate-event gates.

Every signal carries exact evidence excerpts from the retained source text,
provenance labels (live / replay / synthetic), and quality flags. Missing
scores are null — unknown is not neutral.

## Layout

```
backend/app/core      signal contract (Pydantic)
backend/app/nlp       sentiment, event classification, pipeline
backend/app/impact    deterministic impact rubric
backend/app/ingestion news and social source adapters
backend/app/replay    recorded-output replay
backend/app/portfolio Module A rebalancer and demo fixtures
backend/app/api       FastAPI routes
backend/tests         pytest suite (49 tests)
frontend/             React dashboard (Vite)
docs/                 architecture, contract, rubric, evaluation, submission
```

## Run

Backend (Python 3.11+):

```
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m uvicorn app.api.main:app --port 8000
```

Frontend (Node 18+):

```
cd frontend
npm install --include=dev
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend.

## Test

```
cd backend
.venv/bin/python -m pytest
```

## API

- `GET /health` — liveness.
- `POST /analyze` — one text -> one company-specific signal.
- `POST /ingest` — batch news/social items; optional recording.
- `POST /replay` — serve recorded signals with no inference.
- `POST /rebalance` — mock-index proposal from supplied signals.

## Demo Notes

Results are mock allocations for demonstration only — not investment advice or
predictions. Synthetic fixtures and recorded replays are labeled in every
response (provenance field).
