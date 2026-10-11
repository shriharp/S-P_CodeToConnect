# Project Status

Last verified: 2026-10-11, against the repository and a passing test run (138 tests).

Baseline: the AI/NLP Risk Engine and Module A are functionally complete and
exceed the core technical bar. Work is now the approved dashboard/infrastructure
plan below (consolidated from `docs/problem-statement.md` plus the design
review). This file is the single source of truth for that plan and is kept
updated throughout development — not just at the start.

Reporting convention for every item: **completed / in progress / blocked /
deferred**, with files touched and tests run recorded on completion.

## Approved Scope — P0 (core deliverables & essential infrastructure)

- [x] **P0.1 Portfolio Decision Ledger.** DONE 2026-10-10. Persist
      original/proposed/final weights; decisions (executed/capped/skipped);
      timestamps; consumed signal IDs; reasons; policy version. Weight-history
      reconstruction via `/portfolio/weight-history`. SQLite `rebalance_events`.
      Files: `app/portfolio/rebalancer.py` (DecisionRecord), `app/storage/ledger.py`,
      `app/api/main.py` (/ledger, /portfolio/weight-history). Tests: 12 in
      `tests/test_ledger.py` (invariants, roundtrip, chronological reconstruction).
- [x] **P0.2 Weight Evolution Timeline.** DONE 2026-10-10. All 10 tickers across
      rebalance events; animated progressive reveal on replay; yfinance price
      overlay indexed to 100; labels distinguish target decisions from market
      drift. `frontend/src/views/Overview.jsx` + `LineChart.jsx`.
- [x] **P0.3 Live Signal Feed.** DONE 2026-10-10. Company/sentiment/impact/event/
      timestamp/source/provenance/flags, 5s polling, HOT-vs-newest sort, live-poll
      trigger. `frontend/src/views/Signals.jsx`.
- [x] **P0.4 Signal → Allocation Drill-Down.** DONE 2026-10-10. Evidence excerpts
      (cleaned, merged, deduped), impact explanation, original→final allocation,
      policy decisions + skip reasons; plus causal "what moved and why" storyboard
      joining each ledger step to its driving signal. `Overview.jsx`, `Signals.jsx`.
- [x] **P0.5 Multi-Company Attribution.** DONE. Article → one signal per resolved
      company (`analyze_item` returns list); Strategy Lab analyzer shows each.
- [x] **P0.6 Data & reproducibility — LIVE-FIRST.** DONE 2026-10-10. GDELT news +
      StockTwits social + yfinance quotes, all free/keyless, graceful degradation,
      re-poll dedup (no stale re-drift). Offline CSVs + demo replay kept as labeled
      fallback. Frontend UX done: HOT ranking, manual input moved to Strategy Lab,
      animated replay, Social chatter label, clickable source links, flag tooltips,
      ledger Before/After/Δ columns. `app/ingestion/live_sources.py`,
      `live_poller.py`, `frontend/src/views/*`.
      KNOWN GAP: GDELT news path unconfirmed live (429 under repeated test
      bursts; needs one clean-network verification).

- [x] **P0.7 Live ingestion reliability foundation.** DONE 2026-10-11.
      Added durable provider health and source-item state in
      `data/ingestion.db`, bounded public-provider retries with exponential
      backoff and `Retry-After`, an optional backend-owned scheduler, and
      `GET /live/health`. The scheduler defaults off for tests and one-off
      development runs; enable it explicitly with
      `INGESTION_SCHEDULER_ENABLED=true`. The current poll cycle remains the
      compatibility path while queue/SSE decoupling is implemented next.
      Files: `backend/app/ingestion/state.py`,
      `backend/app/ingestion/retry.py`, `backend/app/ingestion/scheduler.py`,
      `backend/app/api/main.py`, `frontend/src/views/System.jsx`.

- [x] **P0.8 Durable raw-item analysis queue.** DONE 2026-10-11.
      Live news/social items are persisted in `data/raw_items.db` before NLP
      analysis. Bounded claims, explicit processing/completed/pending retry
      states, attempt tracking, and queue counts are exposed through
      `/live/health`. Existing signal and ledger behavior remains compatible.
      Files: `backend/app/ingestion/queue.py`, `live_poller.py`,
      `app/api/main.py`. Tests: `tests/test_ingestion_queue.py`.

- [x] **P0.9 Live update stream.** DONE 2026-10-11. Added an in-process SSE
      hub and `GET /live/events`; completed manual and scheduled polls publish
      canonical signal summaries. Signals view subscribes with automatic
      EventSource reconnect and retains REST polling as a fallback. No external
      broker is required for the single-process hackathon deployment.
      Files: `backend/app/ingestion/events.py`, `app/api/main.py`,
      `frontend/src/views/Signals.jsx`. Tests: `tests/test_live_events.py`.

- [x] **P0.10 SEC EDGAR source expansion.** DONE 2026-10-11. Added keyless SEC
      submissions metadata for all ten tracked companies, normalized as
      timestamped news items and sent through the durable deduplication/queue
      path. Filing bodies are not copied into the application. Provider health
      tracks SEC separately at a conservative five-minute interval.
      Files: `app/ingestion/live_sources.py`, `live_poller.py`,
      `app/api/main.py`. Tests: `tests/test_sec_sources.py`.

- [x] **P0.11 Allowlisted public RSS expansion.** DONE 2026-10-11. Added
      explicit public Apple, Microsoft, ExxonMobil, and Pfizer newsroom feed
      adapters using RSS/Atom normalization, per-feed failure isolation, source
      links, and publication timestamps. Arbitrary URL scraping remains disabled.
      Files: `app/ingestion/live_sources.py`, `live_poller.py`,
      `app/api/main.py`. Tests: `tests/test_public_rss.py`.

- [x] **P0.12 Provider cursors and health detail.** DONE 2026-10-11.
      Durable provider cursors now track the newest observed source item without
      replacing item-level deduplication. System observability refreshes every
      15 seconds and shows schedule interval, cursor, skipped count, queue
      states, and provider errors.
      Files: `app/ingestion/state.py`, `frontend/src/views/System.jsx`.
      Tests: `tests/test_provider_cursor.py`.

## Approved Scope — P1 (high-value dashboard)

- [x] **P1.1 Sector Exposure Heatmap.** DONE 2026-10-10. Aggregates the 10
      tickers' weights by sector (real yfinance sector metadata) from first to
      latest rebalance: Start / Now / Δ columns plus a concentration bar whose
      length + opacity scale with exposure. Sector concentration *constraints*
      remain a separate policy feature (not implemented, by design).
      `frontend/src/views/Portfolio.jsx`.
- [x] **P1.2 Unified What-If / Risk Policy Simulator.** DONE 2026-10-10. Added
      read-only `POST /simulate` — same real rebalancer engine (caps, gates,
      renormalization) but no ledger append, so experiments never pollute the
      audited ledger/weight-history. Strategy Lab switched to it. Impact remains
      display-only. Verified: /simulate leaves ledger+history unchanged;
      /rebalance still persists. Tests: `tests/test_simulate.py`.
      `backend/app/api/main.py`, `frontend/src/views/StrategyLab.jsx`.
- [x] **P1.3 Market Risk Overview.** DONE 2026-10-10. `GET /signals/overview`
      computes descriptive distributions over persisted signals (event-category
      counts, sentiment pos/neutral/neg split + mean, impact mean, null counts) —
      counts only, nulls counted not imputed. Signals tab panel shows KPIs +
      event-category bar chart. Exposure-weighted risk not implemented (no
      exposure data at signal level; deliberately omitted rather than faked).
      `backend/app/api/main.py`, `frontend/src/views/Signals.jsx`.
- [x] **P1.4 Portfolio Performance & Benchmarking.** DONE 2026-10-10.
      `GET /portfolio/performance` computes descriptive metrics from real price
      history + recorded weights: window/final-index/max-drawdown/avg-turnover,
      plus strategy vs equal-weight vs buy-and-hold trajectories. STRICTLY
      DESCRIPTIVE — latest recorded weights held constant over the price window;
      no look-ahead, no outperformance claim, insufficient data returns
      `insufficient_data` rather than a fabricated number. Portfolio tab panel
      shows KPIs + the 3-series chart. Transaction costs not modeled (would need
      a cost assumption; omitted rather than invented). 5 tests in
      `tests/test_performance.py`. `app/portfolio/performance.py`,
      `backend/app/api/main.py`, `frontend/src/views/Portfolio.jsx`.
- [x] **P1.5 Model vs Lexicon Comparison.** DONE 2026-10-10. Restructured the
      benchmark harness to `run_benchmark()` returning measured accuracy,
      confusion matrix, per-class recall, and latency per backend (abstentions
      counted separately, excluded from confusion). `GET /benchmark/sentiment`
      serves it (cached; `?refresh=true` re-runs). Strategy Lab panel shows both
      backends side-by-side with methodology + sample size. Measured live, never
      hardcoded; model metrics None + reason if transformers absent. Fixtures
      remain synthetic dev labels (noted in UI). `benchmarks/sentiment_benchmark.py`,
      `backend/app/api/main.py`, `frontend/src/views/StrategyLab.jsx`.

## Approved Scope — P2 (selectively after P0/P1)

- [ ] **P2.1 Historical Replay & Counterfactual Lab.** Build on replay; replay
      historical signals through the real rebalancer; counterfactual reruns with
      modified/excluded inputs; reuse simulator infra; deterministic + labeled.
- [x] **P2.2 Portfolio-wide Signal Aggregation.** DONE 2026-10-11. Related
      same-company/same-event/same-direction signals are aggregated at the
      Module A policy boundary into one consensus adjustment; contradictory
      directions and independent event categories remain separate. Every source
      signal ID remains in the decision ledger.
      `backend/app/portfolio/aggregation.py`,
      `backend/app/portfolio/rebalancer.py`. Tests: aggregation invariant in
      `tests/test_simulate.py`.
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
- **Tab 4 — Strategy Lab / Experimentation:** Unified text-to-What-If / Policy
  Simulator and counterfactual experimentation. Historical replay remains
  deferred. Model evaluation is kept under System / Observability.
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
4. **Phase 4 — Evaluation & polish:** Model vs Lexicon reporting; Replay /
   Counterfactual UI; turnover + transaction-cost reporting; lightweight System
   tab; aggregation + extra policy constraints.
5. **Phase 5 — Final validation:** end-to-end + regression tests; reproducible demo
   verification; docs + README; confirm the demo runs in 5 minutes.

## Verified Implemented Features (unchanged baseline)

- Pydantic v2 signal contract (schema 0.1): bounds, null-vs-neutral,
  evidence-membership, timestamp ordering, quality-flag consistency.
  `backend/app/core/signal_contract.py`
- Two operational source types (news + social). `backend/app/ingestion/adapters.py`
- Sentiment Score [-1, 1]: DistilRoBERTa financial model by default on live
  ingestion/simulation, with explicit lexicon selection and graceful fallback
  (Apache-2.0; 13/15 vs lexicon 8/15; 27 ms/item; 419 MB peak RSS).
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
- [x] LICENSE (MIT) at repo root. DONE 2026-10-10 (placeholder copyright name —
      user must fill in). `LICENSE`
- [x] README rewritten to the mandatory template (candidate name, college email,
      demo video link, sections 1-5). DONE 2026-10-10 — placeholders `[Your Full
      Name]`, `[your_id@college.ac.in]`, `[Your College Name]`, demo/deck links
      must be filled in by user. `README.md`
- [ ] Presentation deck (5-7 slides) at `docs/presentation.pdf`. TODO (user).
- [ ] Demo video (10-min unlisted YouTube), link in README. TODO (user).
- [x] Architecture diagram. DONE 2026-10-10 as editable `docs/architecture.drawio`
      (per user request, not a PNG; open in diagrams.net; export PNG if the form
      requires one). README embeds it.
- [x] Committed `/data` folder. DONE (market CSVs + demo_news.jsonl).
- [x] requirements.txt at root. DONE 2026-10-10 (pinned; torch/transformers
      commented as optional model extras). `requirements.txt`
- [x] Repo public, named `<college>-<candidate-name>-hackathon`. TODO (user).
- [x] Root-level run command in README Quickstart. DONE (in README section 4).

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

## Fresh-clone robustness (2026-10-10)

Verified a base-requirements clone (no torch/transformers) runs end-to-end:
event_backend="finetuned" -> falls back to hybrid -> which now degrades to
keyword-only when transformers is absent (was crashing with ImportError).
Fixed in `events.py` (classify_event_hybrid checks available()) and
`event_model.py` (finetuned_available() checks both checkpoint AND importability).
README Quickstart updated: base install runs offline on keyword/lexicon layer;
optional model backends documented via requirements-model.txt + the two
fine-tune scripts. Committed data (market CSVs, demo replay) means the demo
works with no network and no model download.

## Progress Log

- 2026-10-09: Consolidated dashboard/infrastructure plan adopted (P0/P1/P2,
  five-tab architecture, 5 phases, non-negotiables, 3 decisions). Baseline engine
  + Module A verified at 64 passing tests. No plan code written yet.
- 2026-10-10: P0.1 Decision Ledger complete (merged feat/decision-ledger,
  commit 08c1cae). Per-signal DecisionRecords + weight-history reconstruction,
  SQLite ledger, 12 new tests. Suite at 76.
- 2026-10-10: P0.6 market-data module (feat/market-data). Offline yfinance
  loader + fetch script + committed /data CSVs. Demo seeds from real market
  caps, capped via Option A (respect MAX_WEIGHT, preserve ordering). 7 new
  loader tests. Suite at 83. P0.6 still pending the demo replay sequence.
- 2026-10-10: P0.6 demo replay sequence (feat/demo-replay). Committed
  data/demo_news.jsonl (40 items) + app/replay/demo_sequence.py drives the real
  pipeline + rebalancer deterministically, offline, provenance=replay. Fixed a
  replay freshness bug: analyze_item now accepts an ingested_at override so
  replay stamps signals with event time (live default unchanged). 8 new tests.
  Suite at 91. Phase 1 backend foundations now COMPLETE (P0.1 + P0.6).
- 2026-10-10: Live-first pivot (user directive). AGENTS.md "Data Influx" section
  added: all three influxes LIVE, free/keyless only (GDELT news, StockTwits
  social, yfinance prices). feat/live-ingestion: live_sources.py + live_poller.py
  + POST /live/poll, graceful degradation. feat/live-model-sentiment: live path
  switched to the DistilRoBERTa model backend (lexicon abstained on short social
  posts); added cashtag ($AAPL) resolution to entities.py — StockTwits resolves
  now; fixed a live-poll timestamp-ordering bug (signals were stamped past the
  rebalance clock and rejected as stale). Live poll verified: 8/32 signals
  consumed, real weight adjustments, weights sum to 1.0. 3 new cashtag tests.
  Suite at 99. REMAINING: GDELT news path still returns 429/JSON errors under
  test rate-limiting — needs a clean-network confirmation; frontend UX changes
  (HOT ranking, move manual input to Strategy Lab, animated replay) not started.
- 2026-10-11: Demo/live UX and source enrichment. The frontend now has a
  clearly labeled Demo mode toggle and reusable right-side context rail. Demo
  mode loads the 40-item evidence-bearing replay corpus; it does not download
  or silently redistribute a third-party dataset. Live mode remains the default.
  Public r/stocks RSS was added as optional social enrichment; Reddit carries no
  native sentiment label, so the normal NLP inference and quality gates apply.
  The live poll response now reports per-source counts separately from errors.

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
## P0.13 Dashboard isolation and timeline clarity

- Added explicit live/demo dashboard scopes for signals, ledger events, and
  weight history.
- Prevented Strategy Lab, replay, and test/fixture rows from appearing in live
  dashboard views.
- Excluded no-op rebalance events from the weight-evolution plot.
- Suppressed skipped decisions in weight-change explanations while retaining
  them in the audit ledger.
- Added hover highlighting and stock selection controls to the weight timeline.

## P0.14 Ingestion source inspection and timeline controls

- Added paginated, searchable `GET /live/providers/{provider}/items` inspection
  for durable raw queue records and retained source-item metadata.
- Made System provider rows clickable and exposed raw payloads, queue status,
  attempts, timestamps, and retained errors without starting a new fetch.
- Clarified partial provider success when fetched records exist but one feed
  member fails; historical fetched rows no longer claim that no fetch succeeded.
- Added explicit manual-mode wording and a direct System navigation action in
  the global ingestion runtime rail.
- Added Clear all and removable ticker controls to both Overview charts. Demo
  weight history retains no-op replay steps; live history continues to focus on
  actual allocation changes.
- Validation: full backend suite (138 passed), frontend production build, and
  `git diff --check`.

## P0.15 Scoped portfolio and complete timeline controls

- Added Select all controls alongside Clear all for both Overview plots.
- Live weight history now retains every scoped live rebalance event, including
  no-op events caused by unknown or policy-skipped signals, so ingestion
  activity is visible beyond the previous four movement steps.
- Portfolio now requests the active live/demo scope for ledger, weight history,
  and performance instead of mixing both modes through unscoped `all` data.
- Manual-mode copy now states that browser-triggered polling is the fallback;
  Signals refreshes live data periodically while mounted, and the Poll live
  sources button triggers an immediate cycle. Backend scheduler mode remains
  independent of the browser.
- Validation: full backend suite (138 passed), frontend production build, and
  `git diff --check`.

## P0.16 Scheduler onboarding and stable portfolio presentation

- Added the exact background scheduler startup command and manual-mode
  behavior to `README.md`.
- Sector exposure now uses deterministic alphabetical ordering in both live and
  demo scopes, instead of sorting by current exposure and moving rows between
  modes.
- Decision: demo replay should not be silently substituted into live Overview.
  It is provenance-labeled historical replay with curated evidence and a
  different signal distribution; showing it as live would overstate current
  source coverage and policy actionability. It can be used as a clearly
  labeled reference/baseline view instead.
- Validation: full backend suite (138 passed), frontend production build, and
  `git diff --check`.
