"""Zero-shot NLI event classifier (model backend for event classification).

Replaces the keyword-table event classifier with a pre-trained natural-language-
inference model used zero-shot: each event category is posed as a hypothesis
("This text is about a credit event") and the model scores entailment vs
contradiction. Highest-entailment category wins; abstains (Unknown) when no
category is confidently entailed.

CPU-first, no paid API. Uses transformers' zero-shot pipeline with a small MNLI
model (~270MB, downloads once then cached). Latency ~100ms/item — acceptable for
the demo, and the pipeline object is loaded lazily once per process.

Honesty constraints (AGENTS.md): the model chooses the category, but evidence
excerpts still come from the retained source text (never fabricated), and when no
category clears the confidence floor we return Unknown rather than guessing.
"""

import importlib.util

CHECKPOINT = "typeform/distilbert-base-uncased-mnli"

# Candidate labels, aligned to the contract taxonomy. Plural/specific phrasing
# helps the NLI model map text to the right hypothesis.
LABELS: dict[str, str] = {
    "earnings": "This text is about company earnings, revenue, or financial guidance",
    "operational_disruption": "This text is about an operational outage, shutdown, or disruption",
    "merger_or_acquisition": "This text is about a merger, acquisition, or takeover",
    "regulatory_or_legal": "This text is about a lawsuit, fine, or regulatory action",
    "credit_event": "This text is about a credit default, bankruptcy, or downgrade",
    "product_launch": "This text is about a new product launch or release",
    "commercial_agreement": "This text is about a partnership, contract, or commercial agreement",
    "geopolitical": "This text is about tariffs, war, or geopolitical conflict",
    "macroeconomic": "This text is about macroeconomic policy like inflation or interest rates",
}

_pipeline = None

# Calibrated on app/nlp/event_eval_cases.py (see benchmarks/sentiment_benchmark.py
# run_event_benchmark). With 9 hypotheses, softmax dilutes confidence, so a low
# floor is correct: 0.20 maximizes measured accuracy while still abstaining on
# genuine chatter. Honest finding: the keyword table outperforms this generic
# zero-shot model on our synthetic eval set (see docs/model-evaluation.md).
CONFIDENCE_FLOOR = 0.20


def available() -> bool:
    return importlib.util.find_spec("transformers") is not None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline

        _pipeline = pipeline("zero-shot-classification", model=CHECKPOINT)
    return _pipeline


def classify_event_model(text: str) -> tuple[str, float | None]:
    """Classify text into an event category via zero-shot NLI.

    Returns (category_key, confidence). category_key is one of the LABELS keys,
    or "unknown" when nothing clears CONFIDENCE_FLOOR. The confidence is the
    model's entailment score for the winning label — reported, not hidden.
    """
    pipe = _get_pipeline()
    candidate_labels = list(LABELS.values())
    result = pipe(text, candidate_labels, multi_label=False)
    best_label = result["labels"][0]
    best_score = float(result["scores"][0])
    if best_score < CONFIDENCE_FLOOR:
        return "unknown", best_score
    # Map the winning hypothesis back to the taxonomy key.
    for key, label in LABELS.items():
        if label == best_label:
            return key, best_score
    return "unknown", best_score


FT_DIR = None  # resolved lazily to backend/models/event_classifier
_ft_model = None
_ft_tok = None
_ft_labels = None


def finetuned_available() -> bool:
    """True if a trained checkpoint exists on disk (else caller falls back)."""
    from pathlib import Path

    d = Path(__file__).resolve().parents[2] / "models" / "event_classifier"
    return (d / "config.json").exists()


def _get_finetuned():
    global _ft_model, _ft_tok, _ft_labels, FT_DIR
    if _ft_model is None:
        import json
        from pathlib import Path

        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        FT_DIR = Path(__file__).resolve().parents[2] / "models" / "event_classifier"
        _ft_tok = AutoTokenizer.from_pretrained(FT_DIR)
        _ft_model = AutoModelForSequenceClassification.from_pretrained(FT_DIR)
        _ft_model.eval()
        _ft_labels = json.loads((FT_DIR / "labels.json").read_text())
    return _ft_model, _ft_tok, _ft_labels


def classify_event_finetuned(text: str) -> tuple[str, float | None]:
    """Classify via the fine-tuned DistilRoBERTa event checkpoint.

    Returns (category_key, confidence). Trained on templated synthetic data —
    see docs/model-evaluation.md for the honest caveat and measured numbers.
    """
    import torch

    model, tok, labels = _get_finetuned()
    inputs = tok(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        probs = torch.softmax(model(**inputs).logits[0], dim=-1)
    idx = int(torch.argmax(probs))
    return labels[idx], float(probs[idx])
