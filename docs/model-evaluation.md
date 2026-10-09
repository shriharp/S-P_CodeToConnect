
# Model Evaluation

## Objective
Select lightweight, CPU-compatible NLP models for company-specific financial sentiment and event interpretation.

## Selected Checkpoint (sentiment)

- Checkpoint: `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis`
- Source: Hugging Face; DistilRoBERTa-base, 82M parameters, 6 layers.
- License: Apache-2.0 (verified on the model card, 2026-10-09). Adopted because
  it is financial-domain and permissively licensed.
- Trained on: Financial PhraseBank (financial news sentences).
- Labels: negative / neutral / positive.
- Rejected alternatives: `ProsusAI/finbert` and `yiyanghkust/finbert-tone` —
  no license declared on either model card (default all-rights-reserved);
  not adopted under the license-verification requirement.

### Measured performance (2026-10-09)

Hardware: Apple arm64 (Darwin 25.5.0), 8 CPU cores, no GPU.
Dataset: 15 human-labeled synthetic dev fixtures (`app/nlp/eval_cases.py`).

| Backend | Accuracy | Abstentions | CPU latency | Peak RSS |
|---|---|---|---|---|
| lexicon | 8/15 | 7 | 0.1 ms/item | in-process |
| DistilRoBERTa financial | 13/15 | 0 | 27 ms/item | 419 MB |

Reproduce: `cd backend && .venv/bin/python -m benchmarks.sentiment_benchmark`.

### Known failure cases
- Occasionally labels neutral corporate announcements as weakly positive
  (e.g. a dividend-maintenance sentence scored positive at 0.62 confidence).
- Confidence-scaled magnitude means high-confidence neutrals return 0.0, which
  is correct per the contract (zero = neutral, not unknown).

### Limitations of this evaluation
- 15 synthetic fixtures; useful for development comparison, NOT a real-world
  accuracy claim. Independent, reviewed evaluation data is required before any
  external accuracy claim (see Test Coverage below).
- Measures company-agnostic sentence sentiment only. Multi-company attribution
  and company-specific sentiment remain governed by the entity-resolution and
  pipeline layers, evaluated separately.

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

## Fallback
Provide recorded-output replay for weak hardware.

Do not represent replayed outputs as fresh inference.

## Reporting
Report actual measurements, limitations, and failures.
Do not claim low-resource compatibility without testing.

The lexicon backend remains the default (no model download at runtime); the
model backend is opt-in per request via `sentiment_backend: "model"`.
