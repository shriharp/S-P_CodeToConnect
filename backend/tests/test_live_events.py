from app.ingestion.events import LiveEvent


def test_live_event_encodes_as_server_sent_event():
    encoded = LiveEvent("poll", {"event_id": "live-1"}).encode()
    assert encoded.startswith("event: poll\n")
    assert 'data: {"event_id": "live-1"}' in encoded
    assert encoded.endswith("\n\n")
