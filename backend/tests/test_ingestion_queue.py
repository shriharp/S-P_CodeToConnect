from datetime import datetime, timezone

from app.core.signal_contract import SourceType
from app.ingestion.adapters import RawSourceItem
from app.ingestion.queue import RawItemQueue


def item(external_id: str = "item-1") -> RawSourceItem:
    return RawSourceItem(
        provider="test",
        source_type=SourceType.news,
        external_id=external_id,
        text="Apple reports stronger quarterly revenue.",
        published_at=datetime.now(timezone.utc),
    )


def test_queue_deduplicates_and_transitions_to_complete(tmp_path):
    queue = RawItemQueue(tmp_path / "queue.db")
    assert queue.enqueue(item()) is True
    assert queue.enqueue(item()) is False
    assert queue.counts() == {"pending": 1}

    claimed = queue.claim()
    assert len(claimed) == 1
    rowid, loaded = claimed[0]
    assert loaded.external_id == "item-1"
    assert queue.counts() == {"processing": 1}

    queue.complete(rowid)
    assert queue.counts() == {"complete": 1}
    queue.close()


def test_failed_item_returns_to_pending_with_error(tmp_path):
    queue = RawItemQueue(tmp_path / "queue.db")
    queue.enqueue(item())
    rowid, _ = queue.claim()[0]
    queue.fail(rowid, "temporary provider failure", retry_seconds=0)

    assert queue.counts() == {"pending": 1}
    rowid, loaded = queue.claim()[0]
    assert loaded.external_id == "item-1"
    queue.complete(rowid)
    queue.close()
