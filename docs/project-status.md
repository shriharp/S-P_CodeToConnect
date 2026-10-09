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
- FastAPI endpoints: `/health`, `/analyze`, `/ingest`, `/replay`, `/rebalance`.
  `backend/app/api/main.py`
- React dashboard (Vite): signal analyzer, mock rebalance, ingest & replay tabs.
  `frontend/`
- Test suite: 49 tests passing (contract, rubric, rebalancer, pipeline,
  adapters, replay). `backend/tests/`

## Known Limitations (current)

- Company resolution is not implemented; signals carry
  `unresolved_company` and ticker null. Module A consumes synthetic
  ticker-tagged fixtures instead.
- Sentiment/event NLP is lexicon-based. Model-backed refinement is planned
  and must be benchmarked before adoption (docs/model-evaluation.md).
- No persistence layer; recordings are JSONL files under `backend/recordings/`.
- No containers or CI yet.

## Execution Modes

- Live inference: `/analyze`, `/ingest` with provenance=live.
- Synthetic fixtures: `/rebalance` demo signals, provenance=synthetic.
- Recorded-output replay: `/ingest` with record=true, then `/replay`.
- Fresh historical replay (historical text + fresh inference) is available by
  feeding dated items through `/ingest` with provenance=replay.

## Immediate Priorities

1. Company/entity resolution with ticker mapping.
2. Model-backed sentiment benchmark against lexicon baseline
   (docs/model-evaluation.md).
3. Persistence layer for signals.
4. README, demo script, and submission materials (docs/submission.md).
5. Containerization and license notices (docs/security-licensing.md).

## Status Maintenance Rules

After each meaningful milestone: verify against code and tests, update this
file, keep it short. Never mark functionality complete without a test run.

## Current Blockers

None.

## Next Action

Company/entity resolution so live signals can flow into Module A without
synthetic ticker tagging.
