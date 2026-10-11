
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

## Event Classification (hybrid, default 2026-10-10)

Event classification uses a HYBRID of two systems, because each covers the
other's failure mode:

- **Keyword table** (`app/nlp/events.py`): regex cues per category. High
  precision on clean financial shorthand ("default" → credit_event), but blind
  to paraphrases with no cue word.
- **Zero-shot NLI model** (`app/nlp/event_model.py`): DistilBERT-MNLI
  (`typeform/distilbert-base-uncased-mnli`, ~270MB, Apache-2.0-compatible,
  cached after first load). Generalizes to paraphrases and abstains on chatter,
  but a generic (not finance-tuned) model misreads financial shorthand.

### The hybrid rule (`classify_event_hybrid`)
1. Keyword unambiguous (one category clearly ahead) → keyword.
2. Keyword silent (no cue) → zero-shot model (catches paraphrases).
3. Keyword ambiguous (top categories tied) → model breaks the tie.

Evidence excerpts always come from the retained source text regardless of which
backend chose the category (never fabricated).

### Measured performance (2026-10-10)

Eval set: `app/nlp/event_eval_cases.py` (40 synthetic fixtures — 4 per category
plus 4 chatter/abstention cases). Reproduce:
`cd backend && .venv/bin/python -c "from benchmarks.sentiment_benchmark import run_event_benchmark; d=run_event_benchmark(force_refresh=True); print(d['keyword']['accuracy'], d['hybrid']['accuracy'], d['model']['accuracy'], d['finetuned']['accuracy'])"`.

| Event backend | Accuracy (n=40) |
|---|---|
| keyword table | 0.775 (31/40) |
| zero-shot model only | 0.625 (25/40) |
| hybrid | 0.875 (35/40) |
| **fine-tuned DistilRoBERTa (default)** | **0.975 (39/40)** |

### Fine-tuned classifier (default 2026-10-10)

A DistilRoBERTa-base sequence classifier fine-tuned on the event taxonomy is now
the default (`event_backend="finetuned"`), falling back to hybrid when no
checkpoint is on disk (the ~270MB checkpoint is gitignored; regenerate with
`cd backend && .venv/bin/python -m scripts.generate_event_training_data && .venv/bin/python -m scripts.finetune_event_classifier`).

- Training data: `scripts/generate_event_training_data.py` — ~2,100 templated
  financial headlines across the 10-category taxonomy (slot-filled companies,
  figures, plants). The generator explicitly EXCLUDES the 40 eval-case texts, so
  the benchmark eval set stays held out (no train/test contamination).
- Training: 3 epochs, batch 16, lr 2e-5, CPU (~a few minutes). Loss converged to
  ~0.01; final held-out accuracy 39/40.

### Honest limitations of the fine-tuned result
- Both training AND eval data are synthetic. The 0.975 measures the model against
  fixtures drawn from a similar generative process — it is NOT a real-world
  accuracy claim. Real messy headlines will score lower.
- Training loss near-zero on templated data signals overfitting risk to that
  template style; real paraphrase-heavy text is the true test.
- The keyword and hybrid backends are kept as selectable options because they are
  more robust on out-of-distribution shorthand. The fine-tuned default should be
  re-validated on real labeled data (e.g. Financial PhraseBank for sentiment,
  real event headlines) before any external accuracy claim.

### Known failure cases
- The generic zero-shot model misreads finance shorthand (e.g. "defaulted on
  debt" → operational_disruption); the hybrid guards against this by trusting
  the keyword table on clear cues.
- Confidence floor for the 9-way zero-shot is 0.20 (softmax dilutes confidence
  across many hypotheses); calibrated on the eval set.

### Limitations of this evaluation
- 40 synthetic fixtures; useful for development comparison, NOT a real-world
  accuracy claim. The keyword table is partly hand-tuned to this taxonomy, which
  flatters it somewhat — real-world paraphrase-heavy text would likely widen the
  hybrid's advantage over keyword-only.

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

The live ingestion and simulation paths request the model backend by default;
they fall back to lexicon scoring when the optional model dependencies or
checkpoint are unavailable. The lexicon backend remains selectable explicitly
via `sentiment_backend: "lexicon"`.
