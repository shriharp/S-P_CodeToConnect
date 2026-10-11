import os

import httpx


BASE_URL = os.getenv("RISK_ENGINE_BASE_URL", "http://127.0.0.1:8000")


def test_runtime_sse_endpoint_is_streaming():
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        with client.stream("GET", "/live/events") as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            first_line = next(response.iter_lines())
            assert first_line == ": connected"
