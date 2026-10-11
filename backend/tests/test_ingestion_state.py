from datetime import datetime, timezone

from app.ingestion.state import IngestionState


def test_state_tracks_newest_source_timestamp(tmp_path):
    state = IngestionState(tmp_path / "ingestion.db")
    older = datetime(2026, 10, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 10, 2, tzinfo=timezone.utc)
    state.record_item("sec:edgar", "old", older, "fetched")
    state.record_item("sec:edgar", "new", newer, "analyzed")

    provider = next(row for row in state.health() if row["provider"] == "sec:edgar")
    assert provider["newest_source_at"] == newer.isoformat()
    assert state.seen("sec:edgar", "old") is False
    assert state.seen("sec:edgar", "new") is True
    state.close()
