"""Measure the deterministic impact extractor against the diverse eval set.

Reports band-accuracy (score within expected range) and abstention-correctness.
This is a development benchmark on synthetic fixtures — NOT a real-world
accuracy claim (see docs/model-evaluation.md).
"""

from app.impact import rubric
from app.impact.eval_cases import IMPACT_EVAL_CASES


def _predict(text: str) -> int | None:
    return rubric.score(rubric.extract_factors(text))


def test_band_accuracy_on_eval_set():
    """Most scored cases must land within the expected band."""
    scored = [(t, lo, hi) for t, lo, hi in IMPACT_EVAL_CASES if lo is not None]
    correct = 0
    misses = []
    for text, lo, hi in scored:
        pred = _predict(text)
        if pred is not None and lo <= pred <= hi:
            correct += 1
        else:
            misses.append((text, pred, lo, hi))
    acc = correct / len(scored)
    # Threshold: the extractor must get the majority of scored cases right.
    assert acc >= 0.75, f"band accuracy {acc:.2f} too low; misses={misses}"


def test_abstention_on_neutral_and_negated():
    """Neutral + negated cases must abstain (None), not invent a magnitude."""
    abstain_cases = [(t) for t, lo, hi in IMPACT_EVAL_CASES if lo is None]
    wrong = []
    for text in abstain_cases:
        pred = _predict(text)
        if pred is not None:
            wrong.append((text, pred))
    # Allow at most 1 false-positive abstention leak.
    assert len(wrong) <= 1, f"abstained cases produced scores: {wrong}"


def test_no_case_far_out_of_band():
    """No scored case should be wildly off (e.g. continuity scored as low)."""
    for text, lo, hi in IMPACT_EVAL_CASES:
        if lo is None:
            continue
        pred = _predict(text)
        if pred is None:
            continue
        # Flag egregious misses: off by more than 4 points.
        assert abs(pred - lo) <= 4, f"egregious miss: {text!r} -> {pred} (expected {lo}-{hi})"


def test_qualitative_cases_no_longer_null():
    """The core fix: qualitative headlines must score, not abstain."""
    qualitative = [
        "Apple sales boom in past quarter.",
        "Apple shares soared to a record high.",
        "Apple revenue fell sharply.",
    ]
    for text in qualitative:
        assert _predict(text) is not None, f"qualitative case still null: {text!r}"


def test_negation_still_abstains():
    """Negation handling must suppress magnitude."""
    negated = [
        "Apple avoided any significant decline this quarter.",
        "There was no material impact on operations.",
    ]
    for text in negated:
        assert _predict(text) is None, f"negation not suppressed: {text!r}"
