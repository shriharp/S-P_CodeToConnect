"""Module A: deterministic mock-index rebalancing from risk signals.

Policy (docs/architecture.md + AGENTS.md):
- Sentiment controls adjustment DIRECTION only; impact stays visible but
  does not size adjustments in v1.
- Weights are nonnegative, capped, and renormalized to sum to 100%.
- Signals that fail freshness, quality, or duplicate-event checks are
  excluded from consumption and reported, never silently dropped.
- Output is a mock allocation proposal, not an investment prediction.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.signal_contract import (
    AnalysisStatus,
    QualityFlag,
    RiskSignal,
)

MAX_WEIGHT = 0.25
DEFAULT_STEP = 0.02
FRESHNESS_WINDOW = timedelta(hours=48)
POLICY_VERSION = "module-a-v1"

BLOCKING_FLAGS = {QualityFlag.analysis_error}

DISCLAIMER = (
    "Mock allocation for demonstration only. Not investment advice "
    "or a prediction of future performance."
)


@dataclass
class Portfolio:
    weights: dict[str, float]  # ticker -> weight in [0, 1]
    name: str = "mock-index"

    def __post_init__(self) -> None:
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError("portfolio weights must sum to a positive value")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("portfolio weights must be nonnegative")
        self.weights = {t: w / total for t, w in self.weights.items()}


@dataclass
class DecisionRecord:
    """Auditable per-signal decision. Never fabricated: fields the backend did
    not compute are left None."""

    signal_id: str
    ticker: str | None
    sentiment_score: float | None
    original_weight: float | None  # None when ticker not in portfolio
    proposed_weight: float | None  # weight after this signal, pre-normalization
    final_weight: float | None  # weight after bounded normalization
    decision: str  # "executed" | "capped" | "skipped"
    reason: str | None  # skip/limit reason; None when fully executed


@dataclass
class RebalanceResult:
    proposed_weights: dict[str, float]
    adjustments: dict[str, float]
    original_weights: dict[str, float] = field(default_factory=dict)
    decisions: list[DecisionRecord] = field(default_factory=list)
    policy_version: str = POLICY_VERSION
    consumed_signal_ids: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    disclaimer: str = DISCLAIMER


def _skip_reason(
    signal: RiskSignal, now: datetime, consumed_events: set[str]
) -> str | None:
    if signal.analysis_status is not AnalysisStatus.complete:
        return "analysis_not_complete"
    if signal.ticker is None:
        return "unresolved_company"
    if signal.sentiment_score is None or signal.sentiment_score == 0:
        return "no_directional_sentiment"
    if signal.ingested_at > now or now - signal.ingested_at > FRESHNESS_WINDOW:
        return "stale_or_future_ingested_at"
    if BLOCKING_FLAGS & set(signal.quality_flags):
        return "blocking_quality_flag"
    event_key = f"{signal.company_id}:{signal.event_category.value}:{signal.event_summary[:80]}"
    if event_key in consumed_events:
        return "duplicate_event_already_consumed"
    return None


def rebalance(
    portfolio: Portfolio,
    signals: list[RiskSignal],
    now: datetime,
    step: float = DEFAULT_STEP,
) -> RebalanceResult:
    """Apply eligible signals to the portfolio; return a proposed allocation.

    Emits one DecisionRecord per input signal plus portfolio-level original and
    final weights, so any historical allocation can be reconstructed and audited.
    """
    original = dict(portfolio.weights)
    weights = dict(portfolio.weights)
    consumed_events: set[str] = set()
    consumed: list[str] = []
    skipped: list[dict[str, str]] = []
    decisions: list[DecisionRecord] = []

    for signal in signals:
        reason = _skip_reason(signal, now, consumed_events)
        ticker = signal.ticker
        original_weight = weights.get(ticker) if ticker else None

        if reason is None and ticker not in weights:
            reason = "not_in_portfolio"

        if reason is not None:
            skipped.append({"signal_id": signal.signal_id, "reason": reason})
            decisions.append(
                DecisionRecord(
                    signal_id=signal.signal_id,
                    ticker=ticker,
                    sentiment_score=signal.sentiment_score,
                    original_weight=original_weight,
                    proposed_weight=None,
                    final_weight=None,
                    decision="skipped",
                    reason=reason,
                )
            )
            continue

        delta = step * signal.sentiment_score
        proposed = weights[ticker] + delta
        if proposed < 0:
            proposed = 0.0
        weights[ticker] = proposed
        consumed.append(signal.signal_id)
        event_key = f"{signal.company_id}:{signal.event_category.value}:{signal.event_summary[:80]}"
        consumed_events.add(event_key)
        decisions.append(
            DecisionRecord(
                signal_id=signal.signal_id,
                ticker=ticker,
                sentiment_score=signal.sentiment_score,
                original_weight=original_weight,
                proposed_weight=proposed,
                final_weight=None,  # set after normalization
                decision="executed",
                reason=None,
            )
        )

    weights = _bounded_normalize(weights, MAX_WEIGHT)

    # Fill final weights and mark capped decisions (hit the MAX_WEIGHT ceiling).
    for decision in decisions:
        if decision.ticker in weights:
            decision.final_weight = weights[decision.ticker]
            if (
                decision.decision == "executed"
                and decision.final_weight >= MAX_WEIGHT - 1e-9
            ):
                decision.decision = "capped"
                decision.reason = "reached_max_weight"

    adjustments: dict[str, float] = {}
    for t, w in weights.items():
        delta = w - original[t]
        if abs(delta) > 1e-12:
            adjustments[t] = delta

    return RebalanceResult(
        proposed_weights=weights,
        adjustments=adjustments,
        original_weights=original,
        decisions=decisions,
        consumed_signal_ids=consumed,
        skipped=skipped,
    )


def _bounded_normalize(weights: dict[str, float], cap: float) -> dict[str, float]:
    """Scale to sum 1 while enforcing per-position cap.

    Positions at/over the cap are pinned; the remainder is redistributed
    proportionally among uncapped positions. Raises when caps are jointly
    infeasible (fewer than 1/cap positions).
    """
    n = len(weights)
    if n * cap < 1.0 - 1e-9:
        raise ValueError(
            f"caps infeasible: {n} positions cannot hold 100% at cap {cap:.0%}"
        )
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("all weights zero; cannot normalize")
    scaled = {t: w / total for t, w in weights.items()}

    pinned: set[str] = set()
    while True:
        over = {t for t, w in scaled.items() if w > cap + 1e-12} - pinned
        if not over:
            return scaled
        pinned |= over
        for t in pinned:
            scaled[t] = cap
        free_total = 1.0 - len(pinned) * cap
        free = {t: w for t, w in scaled.items() if t not in pinned}
        free_sum = sum(free.values())
        if free_sum <= 0:
            raise ValueError("caps infeasible: no headroom to redistribute")
        for t in free:
            scaled[t] = free[t] / free_sum * free_total
