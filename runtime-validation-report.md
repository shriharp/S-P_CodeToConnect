# Runtime Validation Report

**Generated**: 2026-10-11T05:37:00Z
**Target**: `/Users/shriharpande/Documents/coding/projects/s-p_code-to-connect_hackathon`

## Summary

| Step | Status | Exit Code | Details |
|------|--------|-----------|---------|
| Docker capability | PASS | 0 | `docker info` succeeded; Docker ServerVersion `29.1.3` |
| Backend startup | PASS | 0 | Existing stale process was replaced; current Uvicorn process served `/health` and `/live/health` |
| Runtime API/SSE tests | PASS | 0 | 3 runtime test files, 3 passed |
| Backend regression suite | PASS | 0 | 135 passed, 0 failed |
| Frontend production build | PASS | 0 | Vite build completed successfully |
| Browser smoke flow | PASS | 0 | Overview → Signals → System; live source-health panel rendered |
| Live provider poll | PASS | 0 | One bounded poll completed; provider errors were returned explicitly |

**Overall**: PASS with documented provider availability gaps.

## Environment

```text
docker: AVAILABLE — Docker daemon responded; server version 29.1.3
node: AVAILABLE — v20.15.0
playwright: AVAILABLE — Chromium launch succeeded after transient package installation
infra-tier: PRIMARY(Docker capability available) — application uses SQLite and did not require a Docker-managed dependency for this run
browser-tier: PRIMARY(Playwright) — headless Chromium smoke flow passed
```

## Runtime Tests

The following runnable tests were executed against `http://127.0.0.1:8000`:

- `backend/tests/runtime_health_test.py`
- `backend/tests/runtime_persistence_test.py`
- `backend/tests/runtime_sse_test.py`

Command:

```text
cd backend && RISK_ENGINE_BASE_URL=http://127.0.0.1:8000 .venv/bin/python -m pytest -q tests/runtime_health_test.py tests/runtime_persistence_test.py tests/runtime_sse_test.py
```

Result: `3 passed in 0.22s`.

The persistence test writes a unique live item, reads it back through the signal API, and exercises the runtime storage path. The SSE test verifies HTTP 200, `text/event-stream`, and the initial `: connected` handshake.

## Browser Evidence

The Playwright smoke flow:

1. Loaded the React application.
2. Opened the Signals view.
3. Opened the System view.
4. Asserted that the Live source health panel was visible.

Result: `browser smoke: passed navigation, Signals, and System live source health`.

## Live Poll Evidence

One bounded `POST /live/poll` request completed successfully. It returned live quotes for all ten tracked companies and source counts including:

- SEC EDGAR: 50 fetched
- Company RSS: 20 fetched
- StockTwits: 59 fetched
- Reddit RSS: 1 fetched
- yfinance: 10 quotes
- Queue: 70 completed

The poll returned no new analyzed signals because the fetched items were either already represented or did not satisfy the current company-specific analysis criteria. This is surfaced through the response and health counters; it is not treated as a fabricated success.

Provider errors observed during this run:

- GDELT: response could not be decoded as JSON
- Pfizer RSS: HTTP 403
- Exxon RSS: HTTP 404
- Several StockTwits symbols: HTTP 403

Other providers, including SEC EDGAR, Reddit RSS, yfinance, and several StockTwits symbols, returned usable live responses. These failures are provider-specific and should be monitored through the System source-health panel.

## Regression Evidence

```text
backend: 135 passed, 4 deprecation warnings
frontend: Vite production build succeeded
git diff --check: clean
```

The backend warnings are FastAPI `on_event` deprecations and do not fail the suite. Migrating to a lifespan handler remains a follow-up cleanup.

## Known Gaps

| # | Severity | Description |
|---|----------|-------------|
| 1 | Medium | GDELT returned a non-JSON response during the live poll; the provider error was retained in health state. |
| 2 | Medium | Some RSS and StockTwits endpoints rejected requests with HTTP 403/404; allowlist/provider configuration should be reviewed periodically. |
| 3 | Low | The scheduler is disabled for this deterministic validation run. Scheduled behavior is covered by unit tests but was not observed as a long-running process here. |
| 4 | Low | The SSE hub is process-local; multi-worker deployment still requires a shared broker or pub/sub layer. |
| 5 | Low | FastAPI startup/shutdown uses deprecated `on_event` hooks. |
