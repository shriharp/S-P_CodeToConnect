# Project Status

Last verified: 2026-10-09, against the repository and a passing test run (64 tests).

Baseline: the AI/NLP Risk Engine and Module A are functionally complete and
exceed the core technical bar. Work is now the approved dashboard/infrastructure
plan below (consolidated from `docs/problem-statement.md` plus the design
review). This file is the single source of truth for that plan and is kept
updated throughout development — not just at the start.

Reporting convention for every item: **completed / in progress / blocked /
deferred**, with files touched and tests run recorded on completion.

## Approved Scope — P0 (core deliverables & essential infrastructure)

- [ ] **P0.1 Portfolio Decision Ledger.** Persist original/proposed/final
      weights; decisions (executed, capped, skipped, stale, duplicate);
      timestamps; consumed signal IDs; policy checks + reasons; policy/algorithm
      version. Must allow historical allocation reconstruction. Reuse SQLite
      patterns. `backend/app/portfolio/`, `backend/app/storage/`
- [ ] **P0.2 Weight Evolution Timeline.** Plot all 10 tickers' weights across
      rebalance events; rebalance markers + explanations; real yfinance price
      overlay; clearly distinguish target-allocation decisions from observed
      market drift. Never present target weights as executed holdings.
- [ ] **P0.3 Live Signal Feed.** Company, sentiment, impact, event, timestamp,
      source, provenance, quality flags, freshness + processing status. Real
      persisted history + polling — no fabricated updates.
- [ ] **P0.4 Signal → Allocation Drill-Down.** Evidence excerpts; sentiment &
      impact explanation; real rubric factors/contributions; original→proposed→
      →final allocation; policy checks, caps, skip reasons. Never fabricate
      factors the backend did not produce.
- [ ] **P0.5 Multi-Company Attribution.** Article → multiple company signals,
      each with its own sentiment/impact/classification/evidence; surface
      contradictory evidence where supported.
- [ ] **P0.6 Data & reproducibility.** Complete yfinance integration + `/data`
      artifacts; committed deterministic demo dataset + replay sequence; reuse
      recorded-output + historical replay; core demo must run without network.

## Approved Scope — P1 (high-value dashboard)

- [ ] **P1.1 Sector Exposure Heatmap.** Add sector metadata for existing 10
      tickers; sector exposure before/after rebalance. Sector concentration
      *constraints* stay a separate policy feature.
- [ ] **P1.2 Unified What-If / Risk Policy Simulator.** Non-persistent (read-only
      by default) simulation endpoint; synthetic sentiment + adjustable supported
      policy params; demonstrate caps + skips; show full weight vector incl. which
      holdings fund an increase; preserve 100% invariant; reuse real rebalancer
      logic (no frontend-only formula). Impact is read-only (does not size).
- [ ] **P1.3 Market Risk Overview** (rename of Impact & Sentiment Radar). Event-
      category distributions, sentiment trends, impact distributions,
      exposure-weighted risk — only where data supports it.
- [ ] **P1.4 Portfolio Performance & Benchmarking.** Historical prices + allocation
      history → portfolio metrics; vs equal-weight and buy-and-hold baselines;
      turnover, transaction costs, drawdown where feasible; timestamp-valid
      chronological evaluation, no look-ahead; clearly distinguish illustrative /
      descriptive / genuinely backtested. Never manufacture metrics.
- [ ] **P1.5 Model vs Lexicon Comparison.** Preserve benchmark; add confusion
      matrix, per-category results, latency comparison; expose methodology + sample
      sizes; measured results only, no hardcoded illustrative values.

## Approved Scope — P2 (selectively after P0/P1)

- [ ] **P2.1 Historical Replay & Counterfactual Lab.** Build on replay; replay
      historical signals through the real rebalancer; counterfactual reruns with
      modified/excluded inputs; reuse simulator infra; deterministic + labeled.
- [ ] **P2.2 Portfolio-wide Signal Aggregation.** Group related items; avoid
      redundant rebalances from duplicate/near-duplicate reports; preserve source
      evidence + signal lineage; never silently merge independent/contradictory
      evidence.
- [ ] **P2.3 Additional Portfolio Constraints.** Prioritize turnover limits +
      funding explanations; defer min-weight, cash policy, sector caps unless
      time allows. Any policy change documented in AGENTS.md + tested.
- [ ] **P2.4 Strategy Ablation.** Deferred evaluation enhancement.
- [ ] **P2.5 Signal-to-Outcome Evaluation.** Deferred research; NOT on critical
      path. No predictive/outperformance claims without valid evidence.

## Five-Tab Frontend Architecture (target UI)

- **Tab 1 — Overview / Command Center:** portfolio KPIs, Weight Evolution
  Timeline, historical price comparison, rebalance markers, recent signal
  preview, latest allocation explanation. (Primary demo screen.)
- **Tab 2 — Signals / NLP Intelligence:** Live Signal Feed, Article Analyzer,
  Multi-Company Attribution, Signal→Allocation Drill-Down, Market Risk Overview,
  provenance + quality flags.
- **Tab 3 — Portfolio / Financial Intelligence:** current holdings, Decision
  Ledger, Sector Exposure Heatmap, Performance & Benchmarking, turnover +
  drawdown, counterfactual comparisons (where implemented).
- **Tab 4 — Strategy Lab / Experimentation:** Unified What-If / Policy Simulator,
  Historical Event Replay, Model vs Lexicon, counterfactual experimentation.
  Deferred features shown only if clearly labeled unavailable, else omitted.
- **Tab 5 — System / Observability (lightweight):** ingestion status/counts,
  source provenance, measured processing latency, data quality/failures, replay +
  reproducibility info, backend status. No heavy monitoring infra.

UI follows a demo-narrative structure while supporting independent exploration
during technical Q&A.

## Non-Negotiable Technical Requirements (in addition to AGENTS.md)

Preserve every existing AGENTS.md invariant unless explicitly changed:
- Weights stay normalized to 100%; caps and gates keep working.
- Impact must NOT silently become an allocation-sizing factor.
- Signals are risk intelligence, not investment predictions.
- Mock allocations are never represented as real trades.
- Preserve publication/ingestion/processing timestamps.
- No look-ahead bias in any historical evaluation.
- Explicit provenance: live / replay / synthetic everywhere.
- Never fabricate evidence, financial metrics, benchmark results, or explanations.
- Keep NLP classification performance separate from portfolio financial performance.
- Persist auditable decision histories.
- CPU-first, minimal dependencies; extend existing contracts/components rather than
  duplicating.
- New simulator endpoint is read-only/non-persistent by default (cannot mutate the
  real demo portfolio state).

## Decisions Taken (from design review)

1. **Index composition:** keep the existing diversified 10 tickers. Add static
   sector metadata for the heatmap; do NOT reshape the index for visual drama.
   Simulator may show a hypothetical concentration scenario separately.
2. **Impact sizing:** impact stays display-only. Simulator shows impact as a
   read-only attribute; no misleading slider. Sentiment + caps + gates size moves.
3. **Signal-to-Outcome:** full forward-return/statistical eval deferred. Retain
   Portfolio Performance & Benchmarking (vs baselines) only if implementable
   correctly with yfinance + weight history; otherwise show descriptive analytics
   and mark evaluation incomplete. No claims of predictive ability.

## Implementation Phases (dependency-aware)

1. **Phase 1 — Backend foundations:** Decision Ledger + persistence; weight-history
   reconstruction; yfinance integration + data prep; schema/API extensions; tests
   for portfolio invariants + ledger correctness.
2. **Phase 2 — Core demo experience:** five-tab shell; Weight Timeline; Live Signal
   Feed; Signal Drill-Down; Multi-Company Attribution; deterministic replay
   walkthrough.
3. **Phase 3 — Portfolio intelligence:** Sector Heatmap; Unified Simulator; Market
   Risk Overview; Performance & Benchmarking (subject to data validity).
4. **Phase 4 — Evaluation & polish:** Model vs Lexicon improvements; Replay /
   Counterfactual UI; turnover + transaction-cost reporting; lightweight System
   tab; optional aggregation + extra policy constraints.
5. **Phase 5 — Final validation:** end-to-end + regression tests; reproducible demo
   verification; docs + README; confirm the demo runs in 5 minutes.

## Verified Implemented Features (unchanged baseline)

- Pydantic v2 signal contract (schema 0.1): bounds, null-vs-neutral,
  evidence-membership, timestamp ordering, quality-flag consistency.
  `backend/app/core/signal_contract.py`
- Two operational source types (news + social). `backend/app/ingestion/adapters.py`
- Sentiment Score [-1, 1]: lexicon (default) + opt-in DistilRoBERTa financial
  model (Apache-2.0; 13/15 vs lexicon 8/15; 27 ms/item; 419 MB peak RSS).
  `docs/model-evaluation.md`
- Event Classification: full taxonomy. `backend/app/nlp/events.py`
- Impact Score [1-10]: deterministic rubric with abstention-to-null.
  `backend/app/impact/rubric.py`
- Structured output via API (7 endpoints) + SQLite + JSONL.
  `backend/app/api/main.py`, `backend/app/storage/`
- Entity resolution (alias registry, 10 mock-index companies). `backend/app/core/entities.py`
- Module A rebalancer: sentiment-direction adjust, 25% cap (bounded
  normalization), freshness + duplicate gates, weights sum 100%.
  `backend/app/portfolio/`
- Recorded-output replay. `backend/app/replay/`
- React dashboard (Vite): 3 thin tabs — to be replaced by the five-tab shell.
- Test suite: 64 passing. `backend/tests/`

## Remaining Problem-Statement Deliverables (separate from dashboard plan)

All mandatory per `docs/problem-statement.md`, tracked but not part of the
P0/P1/P2 dashboard scope:
- [ ] LICENSE (MIT) at repo root.
- [ ] README rewritten to the mandatory template (candidate name, college email,
      demo video link, sections 1-5).
- [ ] Presentation deck (5-7 slides) at `docs/presentation.pdf`.
- [ ] Demo video (10-min unlisted YouTube), link in README.
- [ ] Architecture diagram `docs/architecture.png`.
- [ ] Committed `/data` folder (also serves P0.6).
- [ ] requirements.txt at root (or documented pyproject alternative).
- [ ] Repo public, named `<college>-<candidate-name>-hackathon`.
- [ ] Root-level run command in README Quickstart.

## Known Limitations (current)

- Entity registry: 10 mock-index companies only; others flagged
  `unresolved_company`. No fuzzy/linker resolution.
- Sentiment model is company-agnostic; attribution comes from the alias resolver.
- Impact rubric abstains often by design; bands tuned on synthetic text only.
- No containers or CI.
- Mock-index prices currently static/hardcoded (fixed by P0.6 / yfinance).
- "Real-time ingestion" is on-demand POST + replay; no live feed subscription.

## Execution Modes

- Live inference: `/analyze`, `/ingest` provenance=live (lexicon default;
  `sentiment_backend: "model"` for transformer).
- Synthetic fixtures: `/rebalance` demo signals, provenance=synthetic.
- Recorded-output replay: `/ingest` record=true, then `/replay`.
- Fresh historical replay: feed dated items through `/ingest` provenance=replay.

## Progress Log

- 2026-10-09: Consolidated dashboard/infrastructure plan adopted (P0/P1/P2,
  five-tab architecture, 5 phases, non-negotiables, 3 decisions). Baseline engine
  + Module A verified at 64 passing tests. No plan code written yet.

## Status Maintenance Rules

After each milestone: record what changed, which files were modified, which tests
were run and whether they passed, and what remains incomplete. Keep this file
short in prose but complete in tracking. Never mark functionality complete
without a test run.

## Current Blockers

None.

## Next Action

Phase 1: build the Decision Ledger + weight-history persistence, then yfinance
integration + `/data`, with tests for portfolio invariants and ledger correctness.
