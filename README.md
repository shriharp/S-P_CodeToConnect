# AI/NLP Risk Engine - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Shrihar Pande
**College Email ID:** shrihar.mitmpl2023@learner.manipal.edu
**College / Campus:** MIT, Manipal
**Demo Video Link:** tbd
**Slide Deck Link (if hosted externally):** tbd

## 1. Project Overview / Problem Statement & Approach

Financial risk teams need to turn unstructured text — news headlines and social
posts — into structured, actionable risk signals, then demonstrate a practical
use of that intelligence. This project builds a unified AI/NLP Risk Engine that
does exactly that, and applies it through a tactical mock-index rebalancer
(Module A).

The approach is a modular pipeline. Live text from free, keyless sources (GDELT
for news, StockTwits for social) is normalized, then run through a hybrid NLP
layer that resolves the affected company (names and cashtags), scores
company-specific sentiment, classifies the event type, and computes a financial
impact score with a deterministic rubric that abstains when evidence is thin.
Each result is validated against a strict signal contract: scores have defined
bounds, unknown is never conflated with neutral, and every claim must be backed
by an exact excerpt from the source text.

Those signals then drive Module A: a transparent 10-stock mock index whose
weights move with sentiment, subject to position caps, freshness and
duplicate-event gates, and always renormalized to 100%. Every rebalance is
written to an auditable decision ledger recording the original and final weight,
the decision, and the reason — so any change on the dashboard is traceable back
to the headline that caused it. The system is CPU-first and runs entirely on
free data; a deterministic replay path keeps demos reproducible without a network.

## 2. Architecture & Tech Stack

![Architecture](docs/architecture.drawio)

Editable diagram: `docs/architecture.drawio` (open with diagrams.net).

**Data flow:** live sources → ingestion adapters → NLP pipeline (entity
resolution, sentiment, event, impact rubric) → signal contract validation →
Module A rebalancer → decision ledger → FastAPI → React dashboard.

**Backend:** FastAPI + Pydantic (validation), SQLite (signal store + decision
ledger), yfinance (market data). NLP is a hybrid of a lightweight lexicon layer
(default) and an opt-in DistilRoBERTa financial sentiment model (Apache-2.0,
CPU-viable, ~27 ms/item).

**Frontend:** React (Vite), five tabs — Overview (weight timeline + causal
storyboard), Signals (hot-ranked live feed), Portfolio (ledger, holdings),
Strategy Lab (article analyzer + read-only what-if simulator), System (status,
provenance).

**Key design choices:** deterministic impact scoring (a model never sets the
final impact number), explicit provenance labels (live / replay / synthetic) on
every signal, and a modular layout so the NLP layer, persistence, and portfolio
policy can each be extended independently.

## 3. Dataset Used

- **News:** GDELT Project DOC 2.0 API (free, no key) — live global news.
- **Social media:** StockTwits stream API (free, no key) — live posts with
  symbol context.
- **Market prices:** yfinance (free, no key) — live quotes and history.
- **Entity registry:** a curated, hand-authored alias table for the 10 mock-index
  companies (publicly known large caps). Committed in the repo.

All data is either live from the free sources above or synthetic fixtures clearly
labeled as such in the UI. No proprietary data is used. Assumptions: social posts
are short and often non-directional (the engine abstains rather than guessing);
market-cap-based seed weights are used for the initial mock allocation.

## 4. Quickstart & Installation

Runtime: Python 3.11+ and Node 18+ on macOS/Linux/Windows.

```bash
git clone <your-repo-url>
cd <repo-folder>

# Backend (base install)
cd backend
python -m venv .venv
.venv/bin/pip install -r ../requirements.txt
.venv/bin/python -m uvicorn app.api.main:app --port 8000

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend.

Run tests: `cd backend && .venv/bin/python -m pytest`

### Data: what's included vs what you regenerate

The repo is set up so a fresh clone runs out of the box, offline:

- **Included (committed):** market-price CSVs (`data/market_prices.csv`),
  ticker/sector metadata, and the 40-item demo replay dataset
  (`data/demo_news.jsonl`). The demo replay and market panels work with no
  network and no model download.
- **Not included (regenerate):** the fine-tuned event-classifier checkpoint
  (~270MB) and its training data are gitignored to keep the repo small. They're
  reproducible from the committed scripts.

### Optional: model backends (recommended for the full experience)

The base install runs entirely on the keyword/lexicon layer — no ML downloads
needed, and event classification degrades gracefully to keywords. To enable the
fine-tuned event classifier (default when available) and the model sentiment
backend:

```bash
cd backend
.venv/bin/pip install -r ../requirements.txt -r ../requirements-model.txt
# or: .venv/bin/pip install -e ".[model]"

# Generate training data + fine-tune the event classifier (CPU, a few minutes)
.venv/bin/python -m scripts.generate_event_training_data
.venv/bin/python -m scripts.finetune_event_classifier
```

Without these steps the app still runs — event classification falls back to the
keyword table automatically (see `docs/model-evaluation.md` for measured
accuracy of each backend).

## 5. Key Results & Domain Impact

The engine converts unstructured news and social text into structured,
company-specific risk signals with sentiment, event category, an explainable
impact score, and exact source evidence — validated against a strict contract
that refuses to fabricate scores or evidence. Module A turns those signals into
a transparent mock-index proposal where every weight change is capped, gated,
and traceable in an auditable ledger back to the triggering headline.

This matters because risk and portfolio decisions are only trustworthy when
they are explainable and auditable. The system treats "unknown" as a real state
(not neutral), abstains when evidence is insufficient, and labels data
provenance throughout — the same discipline that separates a credible risk tool
from a black-box sentiment score. It runs on free, CPU-first infrastructure, so
it is reproducible without paid services or a GPU.

---

Mock allocations are for demonstration only — not investment advice or a
prediction of future performance.
