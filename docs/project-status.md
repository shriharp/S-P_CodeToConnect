# Project Status

Last verified: 2026-10-09, against the repository and a passing test run.

## Verified Implemented Features

- Pydantic v2 signal contract (schema 0.1) with score bounds, null-versus-neutral
  semantics, evidence-membership validation, timestamp ordering, and
  quality-state consistency checks. `backend/app/core/signal_contract.py`
- Lexicon NLP layer: company-specific sentiment, primary event classification,
  sentence-level evidence excerpts. `backend/app/nlp/`
- Deterministic impact rubric: factor extraction (quantified loss, breadth,
  duration, continuity cues), banded scoring, lower-band default, abstention
  to null. `backend/app/impact/rubric.py`
- Module A mock-index rebalancer: sentiment-direction adjustments, 25% position
  cap via bounded normalization, freshness window, duplicate-event consumption
  gate, nonnegative weights summing to 100%, skip-reason reporting.
  `backend/app/portfolio/`
- Ingestion adapters for two operational source types (news, social).
  `backend/app/ingestion/adapters.py`
- Recorded-output replay (JSONL record/load, no inference). `backend/app/replay/`
- FastAPI endpoints: `/health`, `/analyze`, `/ingest`, `/replay`, `/rebalance`,
  `/signals`, `/signals/count`. `backend/app/api/main.py`
- React dashboard (Vite): signal analyzer, mock rebalance, ingest & replay tabs.
  `frontend/`
- Test suite: 64 tests passing (contract, rubric, rebalancer, pipeline,
  adapters, replay, storage, entities, model backend). `backend/tests/`
- Entity resolution (alias registry for the 10 mock-index companies); one
  signal per resolved company. `backend/app/core/entities.py`
- Persistence: SQLite signal store behind a swappable `SignalStore` seam;
  signals saved on ingest, queryable via `/signals`. `backend/app/storage/`
- Model-backed sentiment (opt-in `sentiment_backend: "model"`): DistilRoBERTa
  financial checkpoint, Apache-2.0, CPU-viable (27 ms/item, 419 MB peak RSS).
  Benchmarked vs lexicon baseline in `docs/model-evaluation.md`.
  `backend/app/nlp/sentiment_model.py`, `backend/benchmarks/`

## Known Limitations (current)

- Entity registry covers only the 10 mock-index companies; other names are
  flagged `unresolved_company`. No fuzzy/linker-based resolution yet.
- Sentiment model is company-agnostic; company attribution comes from the
  alias resolver, not the model. Multi-company attribution accuracy not yet
  measured on real data.
- Impact rubric is deterministic and abstains often by design; bands tuned on
  synthetic text only.
- No containers or CI yet.

## Execution Modes

- Live inference: `/analyze`, `/ingest` with provenance=live (lexicon default;
  `sentiment_backend: "model"` for the transformer).
- Synthetic fixtures: `/rebalance` demo signals, provenance=synthetic.
- Recorded-output replay: `/ingest` with record=true, then `/replay`.
- Fresh historical replay (historical text + fresh inference) is available by
  feeding dated items through `/ingest` with provenance=replay.

## Immediate Priorities

1. Containerization (Dockerfile) and dependency pinning.
2. Submission materials: demo script, slides, final license notices
   (docs/submission.md, docs/security-licensing.md).
3. Expand entity registry / evaluate linker-based resolution.
4. Real (non-synthetic) evaluation set for accuracy claims.

## Status Maintenance Rules

After each meaningful milestone: verify against code and tests, update this
file, keep it short. Never mark functionality complete without a test run.

## Current Blockers

None.

## Next Action

Containerize the backend + frontend and prepare submission materials.
