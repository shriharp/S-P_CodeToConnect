
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

## Stack
- React frontend.
- FastAPI backend.
- Pydantic validation.
- Database: not yet selected.
- Modular monolith initially.
- Containerization for reproducibility.

Keep ingestion, analysis, persistence, API, and portfolio-policy boundaries distinct.

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
