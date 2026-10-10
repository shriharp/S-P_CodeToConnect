from pathlib import Path

import pytest

from app.market.loader import (
    load_metadata,
    load_prices,
    market_cap_weights,
    TickerMeta,
)
from app.portfolio.demo import demo_portfolio

# Use the committed /data CSVs when present; skip network-dependent cases
# otherwise so the suite stays offline-safe.
DATA_PRICES = Path(__file__).resolve().parents[2] / "data" / "market_prices.csv"
HAS_DATA = DATA_PRICES.exists()


@pytest.mark.skipif(not HAS_DATA, reason="/data CSVs not populated")
def test_load_prices_shape():
    prices = load_prices()
    assert len(prices) == 10
    # Each ticker has a chronological dict of date -> positive close.
    for ticker, series in prices.items():
        assert len(series) > 0
        assert all(v > 0 for v in series.values())


@pytest.mark.skipif(not HAS_DATA, reason="/data CSVs not populated")
def test_load_metadata_covers_all_tickers():
    metas = load_metadata()
    assert {m.ticker for m in metas} == {
        "AAPL", "MSFT", "JPM", "XOM", "PG", "KO", "JNJ", "WMT", "CVX", "PFE",
    }
    assert all(m.market_cap > 0 for m in metas)
    assert all(m.sector for m in metas)


def test_market_cap_weights_normalize():
    metas = [
        TickerMeta("AAA", "a", "Tech", 300.0),
        TickerMeta("BBB", "b", "Tech", 100.0),
    ]
    weights = market_cap_weights(metas)
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert weights["AAA"] == pytest.approx(0.75)
    assert weights["BBB"] == pytest.approx(0.25)


def test_market_cap_weights_rejects_zero_total():
    with pytest.raises(ValueError, match="positive"):
        market_cap_weights([TickerMeta("AAA", "a", "Tech", 0.0)])


def test_missing_csv_raises_not_fabricated(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_prices(tmp_path / "nope.csv")


@pytest.mark.skipif(not HAS_DATA, reason="/data CSVs not populated")
def test_demo_portfolio_seeds_from_market_caps():
    p = demo_portfolio()
    # Weights normalize and cover the full index.
    assert abs(sum(p.weights.values()) - 1.0) < 1e-9
    assert set(p.weights) == {m.ticker for m in load_metadata()}
    # Market-cap weighting puts the largest company (AAPL) at the top.
    assert max(p.weights, key=p.weights.get) == "AAPL"


@pytest.mark.skipif(not HAS_DATA, reason="/data CSVs not populated")
def test_demo_portfolio_seed_respects_cap():
    from app.portfolio.rebalancer import MAX_WEIGHT

    p = demo_portfolio()
    # Cap-aware seeding: no opening position exceeds the policy cap.
    assert max(p.weights.values()) <= MAX_WEIGHT + 1e-9
    assert all(v >= 0 for v in p.weights.values())
