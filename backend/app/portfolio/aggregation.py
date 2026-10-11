"""Batch signal aggregation for Module A.

Signals remain persisted and explainable at their original contract granularity
(one source item, one company, one event). Aggregation happens only when a
rebalance is calculated so related coverage contributes one consensus
adjustment instead of drifting the portfolio once per article.
"""

from collections import defaultdict

from app.core.signal_contract import RiskSignal


def group_related_signals(signals: list[RiskSignal]) -> list[list[RiskSignal]]:
    """Group directional signals by company, event category, and direction.

    Different event categories and conflicting directions are never merged.
    Within one group the rebalancer uses the mean directional sentiment, while
    retaining every source signal ID in the audit decision records.
    """
    groups: dict[tuple[str, str, str], list[RiskSignal]] = defaultdict(list)
    seen_ids: set[str] = set()
    for index, signal in enumerate(signals):
        if signal.signal_id in seen_ids:
            groups[("__duplicate__", signal.signal_id, str(index))].append(signal)
            continue
        seen_ids.add(signal.signal_id)
        if signal.ticker and signal.sentiment_score not in (None, 0):
            direction = "positive" if signal.sentiment_score > 0 else "negative"
            groups[(signal.company_id, signal.event_category.value, direction)].append(signal)
        else:
            groups[(signal.signal_id, signal.signal_id)].append(signal)
    return list(groups.values())
