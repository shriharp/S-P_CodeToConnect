import os
import uuid

import httpx


BASE_URL = os.getenv("RISK_ENGINE_BASE_URL", "http://127.0.0.1:8000")


def test_runtime_ingest_then_read_back():
    source_id = f"runtime-{uuid.uuid4()}"
    payload = {
        "source_type": "news",
        "items": [{
            "id": source_id,
            "headline": "Apple reports stronger quarterly revenue and raises guidance.",
            "url": "https://example.test/runtime",
            "provider": "runtime-test",
            "published_at": "2026-10-11T05:00:00Z",
        }],
        "provenance": "live",
        "sentiment_backend": "lexicon",
        "event_backend": "keyword",
    }
    with httpx.Client(base_url=BASE_URL, timeout=20) as client:
        written = client.post("/ingest", json=payload)
        assert written.status_code == 200
        signals = written.json()
        assert signals
        signal_id = signals[0]["signal_id"]

        read_back = client.get("/signals", params={"limit": 500})
        assert read_back.status_code == 200
        assert any(signal["signal_id"] == signal_id for signal in read_back.json())
