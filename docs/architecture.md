
# Architecture

## Objective
Convert unstructured financial news and social text into company-specific, explainable risk signals, then demonstrate their use through a mock-index rebalancer.

## Pipeline
1. Normalize text and source metadata.
2. Identify affected companies and resolve identities/tickers.
3. Perform company-specific sentiment analysis using lightweight NLP.
4. Classify the primary relevant event using NLP.
5. Extract supported financial-impact facts.
6. Calculate impact using a deterministic rubric.
7. Validate scores, nulls, evidence, and quality flags.
8. Persist the resulting signal.
9. Apply Module A's portfolio policy.

Live source items are first written to a durable SQLite raw-item queue. NLP
workers claim bounded batches and mark each item complete or retryable; fetch
and analysis counts are reported separately.

## Stack
- React frontend.
- FastAPI backend.
- Pydantic validation.
- Database: SQLite for the modular-monolith runtime, with a swappable
  repository seam. Signals, ledger events, provider state, and source-item
  deduplication are durable across browser sessions.
- Modular monolith initially.
- Containerization for reproducibility.

Keep ingestion, analysis, persistence, API, and portfolio-policy boundaries distinct.

## Live ingestion runtime

The live path has two execution modes:

1. A manual `POST /live/poll` cycle for explicit demos and troubleshooting.
2. An optional backend-owned scheduler enabled with
   `INGESTION_SCHEDULER_ENABLED=true`. The scheduler is independent of the
   browser and stops cleanly with the FastAPI process.

Provider state is stored in `data/ingestion.db`, including last attempt and
success times, newest source timestamp, cumulative fetched/analyzed/skipped
counts, provider-specific cursors, errors, and retry state. Cursors are
advisory checkpoints for observability and future incremental provider queries;
item-level deduplication remains the correctness mechanism so late-arriving
items are not lost. Public HTTP requests use bounded retries,
exponential backoff, and `Retry-After` when providers return rate limits or
temporary server failures. `GET /live/health` exposes this state for the
observability screen.

SEC EDGAR submission metadata is polled for the tracked companies as an
authoritative filing source. It is normalized through the same source-item
contract and deduplication path as news and social items.

Selected company/newsroom RSS feeds are an additional allowlisted source. Feed
failures are isolated per provider and arbitrary URL scraping is not enabled.

`GET /live/events` provides server-sent events for completed polls. The hub is
an in-process notification layer only; persistence remains authoritative in
SQLite and the frontend falls back to REST refreshes if the stream disconnects.

Dashboard reads are explicitly scoped to either `live` or `demo`. Live mode
excludes replay rows, strategy-lab experiments, and known test/fixture
providers. Demo mode reads only deterministic replay signals and `demo-*`
ledger events. Strategy Lab remains a read-only counterfactual path and does
not write to either dashboard scope.

`source_provider=unknown` means a caller used the live `/analyze` or `/ingest`
API without identifying its upstream provider. It is not a background provider
and does not mean that NLP returned an unknown event. These attributable live
submissions remain visible in live mode, while Strategy Lab and test providers
are excluded by scope.

System source-health rows are clickable. The provider inspection endpoint
returns paginated queue records, normalized raw payloads, queue attempts and
errors, plus any persisted NLP signals matched by provider and source-item
identifier. Inspection is read-only and does not trigger a fetch.

The weight-evolution history retains scoped ledger events, including no-op
events, so live ingestion activity remains visible even when signals are
unknown or skipped by policy. The Overview cause panel still renders only
actual weight changes and labels no-op steps explicitly. Skipped policy-gated
signals remain auditable in the ledger.

## NLP Strategy
Use a hybrid model-driven/deterministic architecture.

Models:
- Company-specific sentiment.
- Event interpretation/classification.
- Optional evidence-grounded fact extraction.

Deterministic code:
- Entity aliases and normalization.
- Final impact scoring.
- Contract validation.
- Portfolio allocation and risk controls.

A small keyword table must not masquerade as the primary NLP implementation.

## Resource Constraints
- CPU-first local inference.
- No mandatory GPU or paid API.
- No large local conversational LLM.
- Benchmark memory and latency before claiming low-resource support.

## Execution Modes
1. Live ingestion + fresh inference.
2. Historical text + fresh inference.
3. Recorded analysis replay without inference.

Synthetic fixtures are separate from recorded inference outputs. Label every mode clearly.

## Module A
A transparent mock index containing approximately 10-20 stocks.

Sentiment controls proposed weight direction.
Portfolio policy controls adjustment size, normalization, caps, freshness, quality, and duplicate-event consumption.

Impact remains visible but need not affect adjustment size initially.

## Module B
Optional synthetic wholesale-portfolio stress testing.
Only implement after the required core and Module A are complete.

## Scalability
Prefer a modular application.
Introduce workers, queues, or additional services only when measurements justify them.

Measure throughput, latency, peak memory, and bottlenecks before making scalability claims.
