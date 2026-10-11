from datetime import timezone

from app.ingestion import live_sources


def test_sec_filings_normalize_recent_metadata(monkeypatch):
    monkeypatch.setattr(
        live_sources,
        "_get_json",
        lambda url: {
            "name": "Apple Inc.",
            "filings": {
                "recent": {
                    "form": ["4", "8-K", "10-Q"],
                    "accessionNumber": ["x", "0000320193-26-000001", "0000320193-26-000002"],
                    "primaryDocument": ["x.xml", "event.htm", "quarterly.htm"],
                    "filingDate": ["2026-10-01", "2026-10-02", "2026-10-03"],
                }
            },
        },
    )

    items = live_sources.fetch_sec_filings("AAPL", max_records=2)

    assert len(items) == 2
    assert items[0].provider == "sec:edgar"
    assert items[0].external_id == "sec:0000320193:0000320193-26-000001"
    assert items[0].published_at.tzinfo == timezone.utc
    assert items[0].url.endswith("/000032019326000001/event.htm")
    assert "8-K" in items[0].text


def test_sec_filings_reject_unknown_ticker():
    try:
        live_sources.fetch_sec_filings("UNKNOWN")
    except ValueError as exc:
        assert "unsupported SEC ticker" in str(exc)
    else:
        raise AssertionError("unknown ticker should be rejected")
