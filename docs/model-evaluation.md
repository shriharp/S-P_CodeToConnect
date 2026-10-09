
# Model Evaluation

## Objective
Select lightweight, CPU-compatible NLP models for company-specific financial sentiment and event interpretation.

## Candidates
- FinBERT-family financial sentiment models.
- Compact DistilBERT-family models.
- Other appropriately licensed lightweight alternatives.

No checkpoint has been selected yet.

## Selection Criteria
For each candidate, record:
- Exact checkpoint, revision, and source.
- License and redistribution restrictions.
- Download size and peak RAM.
- CPU inference latency and throughput.
- Company-specific sentiment performance.
- Multi-company attribution performance.
- Event-classification performance.
- Behavior on ambiguity and missing evidence.

## Evaluation Requirements
Evaluate these tasks separately:
1. Affected-company identification.
2. Company-specific sentiment.
3. Event classification.
4. Impact-fact extraction.
5. Abstention when evidence is insufficient.

Financial sentiment classification alone does not solve the complete pipeline.

## Test Coverage
Include:
- Positive/negative, low/high-impact events.
- Neutral announcements.
- Multi-company articles.
- Unverified and conflicting claims.
- Missing impact evidence.
- Duplicate and outdated reporting.
- Unresolved company identities.
- Text with no affected company.

Synthetic fixtures are useful for development but do not establish real-world accuracy.

## Benchmarking
Record:
- Hardware and operating system.
- Model version.
- Peak RAM.
- CPU latency.
- Batch throughput.
- Correctness and failure cases.
- Abstention and exclusion counts.

Use independently reviewed, appropriately licensed examples before making accuracy claims.

## Fallback
Provide recorded-output replay for weak hardware.

Do not represent replayed outputs as fresh inference.

## Reporting
Report actual measurements, limitations, and failures.
Do not claim low-resource compatibility without testing.
