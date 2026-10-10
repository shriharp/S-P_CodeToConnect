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
from app.nlp.event_eval_cases import EVENT_EVAL_CASES
from app.nlp.sentiment import score_sentiment as lexicon_score

CLASSES = (-1, 0, 1)
_cache: dict | None = None
_event_cache: dict | None = None


def _run_event_backend(classify_fn) -> dict:
    """Run one event classifier over EVENT_EVAL_CASES; return measured accuracy.

    Reports overall accuracy plus per-category recall. Abstentions (unknown)
    are scored like any other prediction — an incorrect abstention is a miss.
    """
    correct = 0
    per_total: dict[str, int] = {}
    per_correct: dict[str, int] = {}
    confusion: dict[str, dict[str, int]] = {}
    for text, gold in EVENT_EVAL_CASES:
        pred = classify_fn(text)
        per_total[gold] = per_total.get(gold, 0) + 1
        confusion.setdefault(gold, {})
        confusion[gold][pred] = confusion[gold].get(pred, 0) + 1
        if pred == gold:
            correct += 1
            per_correct[gold] = per_correct.get(gold, 0) + 1
    n = len(EVENT_EVAL_CASES)
    return {
        "total": n,
        "correct": correct,
        "accuracy": round(correct / n, 4) if n else None,
        "per_category_recall": {
            k: round(per_correct.get(k, 0) / v, 4) for k, v in per_total.items()
        },
        "confusion": confusion,
    }


def run_event_benchmark(force_refresh: bool = False) -> dict:
    """Measured keyword-vs-model event classification. Cached after first run."""
    global _event_cache
    if _event_cache is not None and not force_refresh:
        return _event_cache

    from app.nlp.events import classify_event

    keyword = _run_event_backend(lambda t: classify_event(t)[0].name)

    model = None
    model_reason = None
    if __import__("importlib.util", fromlist=["find_spec"]).find_spec("transformers"):
        from app.nlp.event_model import classify_event_model

        classify_event_model("warmup")  # exclude one-time model load
        model = _run_event_backend(lambda t: classify_event_model(t)[0])
    else:
        model_reason = "transformers not installed (model backend unavailable)"

    _event_cache = {
        "sample_size": len(EVENT_EVAL_CASES),
        "methodology": (
            "Accuracy over all cases; abstentions (unknown) scored as predictions. "
            "FIXTURES ARE SYNTHETIC dev labels — not a real-world accuracy claim."
        ),
        "keyword": keyword,
        "model": model,
        "model_unavailable_reason": model_reason,
    }
    return _event_cache


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
