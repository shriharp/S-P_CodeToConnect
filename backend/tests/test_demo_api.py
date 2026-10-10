from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_market_prices_offline_shape():
    r = client.get("/market/prices", params={"tickers": "AAPL"})
    assert r.status_code == 200
    data = r.json()
    assert list(data.keys()) == ["AAPL"]
    # date -> positive close
    closes = list(data["AAPL"].values())
    assert len(closes) > 0
    assert all(v > 0 for v in closes)


def test_market_prices_filter_unknown_ticker_empty():
    r = client.get("/market/prices", params={"tickers": "ZZZZ"})
    assert r.status_code == 200
    assert r.json() == {}


def test_market_sectors_shape():
    r = client.get("/market/sectors")
    assert r.status_code == 200
    data = r.json()
    assert "AAPL" in data
    assert {"company_id", "sector", "market_cap"} <= set(data["AAPL"].keys())


def test_demo_replay_shape_and_normalization():
    r = client.post("/demo/replay")
    assert r.status_code == 200
    steps = r.json()
    assert len(steps) >= 10
    step = steps[0]
    assert {"item_id", "published_at", "event_id", "signals", "final_weights"} <= set(step.keys())
    assert {"signal_id", "ticker", "decision", "reason", "final_weight"} <= set(
        step["decisions"][0].keys()
    )
    # Weights stay normalized at every step.
    for s in steps:
        assert abs(sum(s["final_weights"].values()) - 1.0) < 1e-9


def test_demo_replay_persists_to_ledger_and_signals():
    r = client.post("/demo/replay")
    assert r.status_code == 200
    # Ledger and signal store are populated by the replay (real SQLite stores).
    assert len(client.get("/ledger").json()) >= 10
    assert client.get("/signals/count").json()["count"] >= 10
