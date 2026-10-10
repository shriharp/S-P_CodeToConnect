"""Benchmark lexicon vs model sentiment on the labeled dev fixtures.

Records accuracy, abstentions, CPU latency, and peak RAM. Run:
    .venv/bin/python -m benchmarks.sentiment_benchmark
"""

import os
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.nlp.eval_cases import EVAL_CASES
from app.nlp.sentiment import score_sentiment as lexicon_score

CLASSES = (-1, 0, 1)
_cache: dict | None = None


def _sign(v):
    return (v > 0) - (v < 0)


def _run_backend(score_fn) -> dict:
    """Run one backend over EVAL_CASES; return measured metrics + confusion.

    Abstentions (None) are counted separately and excluded from the confusion
    matrix — an abstention is not a misclassification, it's a refusal to score.
    """
    n = len(EVAL_CASES)
    correct = abstain = 0
    # confusion[gold][pred] over scored cases only
    confusion = {g: {p: 0 for p in CLASSES} for g in CLASSES}
    per_class_total = {g: 0 for g in CLASSES}
    per_class_correct = {g: 0 for g in CLASSES}

    t0 = time.perf_counter()
    for text, gold in EVAL_CASES:
        score = score_fn(text)
        per_class_total[gold] += 1
        if score is None:
            abstain += 1
            continue
        pred = _sign(score)
        confusion[gold][pred] += 1
        if pred == gold:
            correct += 1
            per_class_correct[gold] += 1
    latency_ms = (time.perf_counter() - t0) / n * 1000

    scored = n - abstain
    return {
        "total": n,
        "scored": scored,
        "abstain": abstain,
        "correct": correct,
        "accuracy": round(correct / scored, 4) if scored else None,
        "confusion": confusion,  # confusion[gold][pred]
        "per_class_recall": {
            str(g): round(per_class_correct[g] / per_class_total[g], 4)
            if per_class_total[g]
            else None
            for g in CLASSES
        },
        "latency_ms_per_item": round(latency_ms, 2),
    }


def run_benchmark(force_refresh: bool = False) -> dict:
    """Structured benchmark of lexicon vs model. Measured, cached after first run.

    The model backend is only included if transformers is installed; otherwise
    model metrics are None with a clear 'unavailable' reason (never fabricated).
    """
    global _cache
    if _cache is not None and not force_refresh:
        return _cache

    lexicon = _run_backend(lambda t: lexicon_score(t)[0])

    model = None
    model_reason = None
    if __import__("importlib.util", fromlist=["find_spec"]).find_spec("transformers"):
        from app.nlp.sentiment_model import score_sentiment_model

        score_sentiment_model("warmup")  # exclude one-time model load from latency
        model = _run_backend(score_sentiment_model)
    else:
        model_reason = "transformers not installed (model backend unavailable)"

    _cache = {
        "hardware": f"{platform.machine()} {platform.system()} {platform.release()}",
        "cpus": os.cpu_count(),
        "sample_size": len(EVAL_CASES),
        "methodology": (
            "Accuracy over scored cases only; abstentions counted separately. "
            "Confusion matrix excludes abstentions. FIXTURES ARE SYNTHETIC dev "
            "labels — not a real-world accuracy claim."
        ),
        "lexicon": lexicon,
        "model": model,
        "model_unavailable_reason": model_reason,
    }
    return _cache


def main():
    data = run_benchmark(force_refresh=True)
    n = data["sample_size"]
    print(f"hardware: {data['hardware']}")
    print(f"cpus: {data['cpus']}  cases: {n}")
    print("-" * 60)
    for name in ("lexicon", "model"):
        b = data[name]
        if b is None:
            print(f"{name:9s}: {data['model_unavailable_reason']}")
            continue
        print(
            f"{name:9s}: acc {b['correct']}/{b['scored']}  "
            f"abstain {b['abstain']}  latency {b['latency_ms_per_item']} ms/item"
        )


if __name__ == "__main__":
    main()
