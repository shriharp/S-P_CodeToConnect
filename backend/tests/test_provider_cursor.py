from datetime import datetime, timezone

from app.ingestion.state import IngestionState


def test_provider_cursor_tracks_latest_item(tmp_path):
    state = IngestionState(tmp_path / "ingestion.db")
    state.record_item(
        "stocktwits", "message-old", datetime(2026, 10, 1, tzinfo=timezone.utc), "fetched"
    )
    state.record_item(
        "stocktwits", "message-new", datetime(2026, 10, 2, tzinfo=timezone.utc), "fetched"
    )
    provider = next(row for row in state.health() if row["provider"] == "stocktwits")
    assert provider["cursor"] == "message-new"
    state.close()
