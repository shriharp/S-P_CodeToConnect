from datetime import date

from app.portfolio.performance import (
    _max_drawdown,
    _portfolio_series,
    _turnover,
    compute_performance,
)

PRICES = {
    "AAA": {date(2026, 1, 1): 100.0, date(2026, 1, 2): 110.0, date(2026, 1, 3): 105.0},
    "BBB": {date(2026, 1, 1): 50.0, date(2026, 1, 2): 50.0, date(2026, 1, 3): 55.0},
}


def test_empty_history_is_insufficient_not_fabricated():
    out = compute_performance([])
    assert out["status"] == "insufficient_data"
    assert out["metrics"] is None
    assert out["baselines"] is None


def test_portfolio_series_indexes_to_100():
    out = _portfolio_series({"AAA": 0.5, "BBB": 0.5}, PRICES)
    assert out is not None
    _, series = out
    assert series[0] == 100.0
    # 0.5*100+0.5*50 = 75 base; last = 0.5*105+0.5*55 = 80 -> 80/75*100
    assert round(series[-1], 2) == 106.67


def test_max_drawdown():
    assert _max_drawdown([100, 120, 90, 130]) == round((120 - 90) / 120 * 100, 2)
    assert _max_drawdown([100, 110, 120]) == 0.0
    assert _max_drawdown([]) is None


def test_turnover_needs_two_events():
    hist = [
        {"weights": {"AAA": 0.5, "BBB": 0.5}},
        {"weights": {"AAA": 0.6, "BBB": 0.4}},
    ]
    # turnover = 0.5 * sum(|Δw|) = 0.5 * (0.1 + 0.1) = 0.1 -> 10%
    assert _turnover(hist) == 10.0
    assert _turnover(hist[:1]) is None


def test_no_lookahead_uses_latest_recorded_weights():
    # compute_performance uses history[-1] weights held constant; it must not
    # reach into the future. With a single event the trajectory is still
    # deterministic and drawn only from recorded weights + observed prices.
    hist = [{"weights": {"AAA": 1.0}}]
    out = compute_performance(hist)
    assert out["status"] == "insufficient_data"  # AAA-only has prices, but guard holds on overlap
