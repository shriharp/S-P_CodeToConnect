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


def _sign(v):
    return (v > 0) - (v < 0)


def bench_lexicon():
    abstain, correct = 0, 0
    t0 = time.perf_counter()
    for text, gold in EVAL_CASES:
        score = lexicon_score(text)[0]
        if score is None:
            abstain += 1
            continue
        if _sign(score) == gold:
            correct += 1
    latency = (time.perf_counter() - t0) / len(EVAL_CASES) * 1000
    return correct, abstain, latency


def bench_model():
    import resource

    from app.nlp.sentiment_model import score_sentiment_model

    abstain, correct = 0, 0
    score_sentiment_model("warmup loading model")  # exclude load time
    t0 = time.perf_counter()
    for text, gold in EVAL_CASES:
        score = score_sentiment_model(text)
        if score is None:
            abstain += 1
            continue
        if _sign(score) == gold:
            correct += 1
    latency = (time.perf_counter() - t0) / len(EVAL_CASES) * 1000
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024
    return correct, abstain, latency, peak_mb


def main():
    n = len(EVAL_CASES)
    print(f"hardware: {platform.machine()} {platform.processor()}")
    print(f"os: {platform.system()} {platform.release()}")
    print(f"cpus: {os.cpu_count()}  cases: {n}")
    print("-" * 60)

    c, a, ms = bench_lexicon()
    print(f"lexicon  : acc {c}/{n}  abstain {a}  latency {ms:.1f} ms/item")

    c, a, ms, mb = bench_model()
    print(f"model    : acc {c}/{n}  abstain {a}  latency {ms:.1f} ms/item  peakRSS {mb:.0f} MB")


if __name__ == "__main__":
    main()
