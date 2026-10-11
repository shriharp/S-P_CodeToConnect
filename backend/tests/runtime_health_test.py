import os

import httpx


BASE_URL = os.getenv("RISK_ENGINE_BASE_URL", "http://127.0.0.1:8000")


def test_runtime_health_and_ingestion_health():
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        ingestion = client.get("/live/health")
        assert ingestion.status_code == 200
        body = ingestion.json()
        assert "providers" in body
        assert "queue" in body
        assert any(row["provider"] == "sec:edgar" for row in body["providers"])
