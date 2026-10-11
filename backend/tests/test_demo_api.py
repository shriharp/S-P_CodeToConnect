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


def test_simulate_text_analyzes_without_persisting():
    before = client.get("/signals/count").json()["count"]
    r = client.post(
        "/simulate-text",
        json={
            "text": "Apple cut revenue guidance after a factory shutdown.",
            "source_item_id": "what-if-test",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert any(signal["ticker"] == "AAPL" for signal in data["signals"])
    assert "proposed_weights" in data["result"]
    assert client.get("/signals/count").json()["count"] == before


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


def test_dashboard_scopes_keep_demo_rows_out_of_live_view():
    replay = client.post("/demo/replay")
    assert replay.status_code == 200
    demo_events = client.get("/ledger", params={"dashboard": "demo"}).json()
    live_events = client.get("/ledger", params={"dashboard": "live"}).json()
    assert demo_events
    assert all(event["event_id"].startswith("demo-") for event in demo_events)
    assert all(
        event["event_id"].startswith(("live-", "scheduled-"))
        for event in live_events
    )

    demo_signals = client.get("/signals", params={"dashboard": "demo"}).json()
    live_signals = client.get("/signals", params={"dashboard": "live"}).json()
    assert demo_signals
    assert all(signal["provenance"] == "replay" for signal in demo_signals)
    assert all(signal["provenance"] == "live" for signal in live_signals)
    assert all(signal["source_provider"] not in {"strategy-lab", "test", "unknown"} for signal in live_signals)


def test_weight_history_excludes_no_change_events():
    response = client.get("/portfolio/weight-history", params={"dashboard": "demo"})
    assert response.status_code == 200
    for row in response.json():
        assert row["weights"]
