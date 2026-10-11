from datetime import timezone

from app.ingestion import live_sources


def test_allowlisted_rss_normalizes_rss_items(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"""<rss><channel>
              <item><title>Apple announces quarterly results</title>
              <link>https://example.test/apple</link>
              <guid>guid-1</guid>
              <pubDate>Sun, 11 Oct 2026 05:00:00 GMT</pubDate></item>
            </channel></rss>"""

    monkeypatch.setattr(
        live_sources,
        "request_with_backoff",
        lambda request, **kwargs: Response(),
    )

    items = live_sources.fetch_public_rss("apple", live_sources.RSS_FEEDS["apple"])

    assert len(items) == 1
    assert items[0].provider == "rss:apple"
    assert items[0].external_id == "guid-1"
    assert items[0].published_at.tzinfo == timezone.utc


def test_rss_rejects_non_allowlisted_url():
    try:
        live_sources.fetch_public_rss("apple", "https://example.test/feed.xml")
    except ValueError as exc:
        assert "not allowlisted" in str(exc)
    else:
        raise AssertionError("non-allowlisted URL should be rejected")
