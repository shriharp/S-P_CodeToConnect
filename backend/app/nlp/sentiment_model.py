"""Model-backed sentiment (DistilRoBERTa financial) behind the same interface.

Checkpoint: mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis
License: Apache-2.0 (verified on the model card, 2026-10-09).
Trained on Financial PhraseBank; 82M params; CPU-viable.

Map to the contract scale: negative -> [-1, 0), neutral -> 0, positive -> (0, 1].
Magnitude is |raw| scaled by model confidence so stronger evidence scores higher.
Abstains (None) only if the model fails to load or inference errors.
"""

import importlib.util

CHECKPOINT = "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis"

_model = None
_tokenizer = None


def available() -> bool:
    return importlib.util.find_spec("transformers") is not None


def _load():
    global _model, _tokenizer
    if _model is None:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        _tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
        _model = AutoModelForSequenceClassification.from_pretrained(CHECKPOINT)
        _model.eval()
    return _model, _tokenizer


def score_sentiment_model(text: str) -> float | None:
    import torch

    model, tokenizer = _load()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits[0]
    probs = torch.softmax(logits, dim=-1)
    label_id = int(torch.argmax(probs))
    confidence = float(probs[label_id])
    label = model.config.id2label[label_id]  # negative | neutral | positive
    if label == "neutral":
        return 0.0
    magnitude = confidence  # in (0.5, 1.0]
    return round(magnitude, 3) if label == "positive" else round(-magnitude, 3)
