"""Descriptive portfolio performance analytics (Module A).

Computes portfolio-value trajectory, drawdown, turnover, and baseline
comparisons (equal-weight, buy-and-hold) from real price history + the recorded
weight history. STRICTLY DESCRIPTIVE — this is not a predictive backtest and
makes no outperformance claim.

Honesty constraints (AGENTS.md / problem statement):
- No look-ahead: the allocation used for a window is the latest RECORDED weight
  at or before that window's start; we never peek forward.
- Nulls/gaps are skipped, never fabricated. Metrics with insufficient data
  return None rather than a made-up number.
- Clearly labeled as descriptive, not a validated backtest.
"""

from datetime import date

from app.market.loader import load_prices
from app.portfolio.rebalancer import DISCLAIMER  # reuse the mock-alloc disclaimer


def _portfolio_series(
    weights: dict[str, float], prices: dict[str, dict[date, float]]
) -> tuple[list[date], list[float]] | None:
    """Value trajectory (indexed to 100) for a fixed weight vector, using dates
    where every held ticker has a price. Returns None if too few dates."""
    tickers = [t for t, w in weights.items() if w > 0]
    if not tickers:
        return None
    common = sorted(set.intersection(*(set(prices.get(t, {})) for t in tickers)))
    if len(common) < 2:
        return None
    base_date = common[0]
    base_val = sum(weights[t] * prices[t][base_date] for t in tickers)
    if base_val <= 0:
        return None
    dates = common
    series = [
        sum(weights[t] * prices[t][d] for t in tickers) / base_val * 100 for d in dates
    ]
    return dates, series


def _max_drawdown(series: list[float]) -> float | None:
    if not series:
        return None
    peak = series[0]
    max_dd = 0.0
    for v in series:
        peak = max(peak, v)
        if peak > 0:
            max_dd = max(max_dd, (peak - v) / peak)
    return round(max_dd * 100, 2)


def _turnover(history: list[dict]) -> float | None:
    """Average per-rebalance turnover (sum of |Δweight| / 2), from recorded
    events. None if fewer than 2 events (nothing to compare)."""
    if len(history) < 2:
        return None
    turns = []
    for prev, cur in zip(history, history[1:]):
        pw, cw = prev["weights"], cur["weights"]
        tickers = set(pw) | set(cw)
        total = sum(abs(cw.get(t, 0) - pw.get(t, 0)) for t in tickers)
        turns.append(total / 2)
    return round(sum(turns) / len(turns) * 100, 2)


def compute_performance(history: list[dict]) -> dict:
    """Descriptive performance summary. history = /portfolio/weight-history rows.

    Returns {status, note, metrics, baselines}. status is 'ok' or
    'insufficient_data'; never fabricates numbers when data is thin.
    """
    prices = load_prices()
    disclaimer = DISCLAIMER

    if not history:
        return {
            "status": "insufficient_data",
            "note": "No rebalance events recorded yet. Run the demo replay or poll live sources first.",
            "metrics": None,
            "baselines": None,
            "disclaimer": disclaimer,
        }

    latest_weights = history[-1]["weights"]
    strat = _portfolio_series(latest_weights, prices)
    if strat is None:
        return {
            "status": "insufficient_data",
            "note": "Not enough overlapping price history to compute a trajectory.",
            "metrics": None,
            "baselines": None,
            "disclaimer": disclaimer,
        }
    dates, series = strat

    # Baselines: equal-weight and buy-and-hold (start-of-window weights held).
    n = len(latest_weights)
    equal = {t: 1.0 / n for t in latest_weights} if n else {}
    eq = _portfolio_series(equal, prices)
    # Buy-and-hold: seed from the FIRST recorded weights, held constant.
    first_weights = history[0]["weights"]
    bh = _portfolio_series(first_weights, prices)

    return {
        "status": "ok",
        "note": (
            "Descriptive only — computed from the latest recorded target weights "
            "held constant over the price window. NOT a predictive backtest; no "
            "outperformance is claimed. Weights are proposed mock allocations."
        ),
        "metrics": {
            "window_days": len(dates),
            "start_date": dates[0].isoformat(),
            "end_date": dates[-1].isoformat(),
            "final_index": round(series[-1], 2),
            "max_drawdown_pct": _max_drawdown(series),
            "turnover_pct": _turnover(history),
            "rebalance_events": len(history),
        },
        "baselines": {
            "strategy": [round(v, 2) for v in series],
            "equal_weight": [round(v, 2) for v in eq[1]] if eq else None,
            "buy_and_hold": [round(v, 2) for v in bh[1]] if bh else None,
            "dates": [d.isoformat() for d in dates],
        },
        "disclaimer": disclaimer,
    }
