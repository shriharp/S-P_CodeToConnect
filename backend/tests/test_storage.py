from datetime import datetime, timedelta, timezone

from app.core.signal_contract import (
    AnalysisStatus,
    EventCategory,
    Provenance,
    QualityFlag,
    RiskSignal,
    SourceType,
)
from app.storage.signals import InMemorySignalStore, SqliteSignalStore

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def make_signal(signal_id="sig-1", ticker="AAPL", ingested_at=NOW):
    return RiskSignal(
        signal_id=signal_id,
        source_item_id="item-1",
        source_provider="test",
        source_type=SourceType.news,
        ingested_at=ingested_at,
        published_at=ingested_at,
        provenance=Provenance.live,
        company_id="apple",
        company_name="Apple Inc.",
        ticker=ticker,
        event_category=EventCategory.earnings,
        event_summary="Earnings missed estimates.",
        sentiment_score=-0.5,
        impact_score=None,
        impact_explanation=None,
        evidence_excerpts=[],
        analysis_status=AnalysisStatus.complete,
        quality_flags={QualityFlag.insufficient_evidence},
        analyzed_at=ingested_at,
        analysis_method_version="test",
    )


def run_contract(store):
    assert store.count() == 0
    store.save(make_signal())
    store.save(make_signal(signal_id="sig-2", ticker="MSFT"))
    assert store.count() == 2
    assert store.list(ticker="aapl")[0].signal_id == "sig-1"
    assert len(store.list()) == 2
    store.save(make_signal(signal_id="sig-1", ticker="AAPL"))  # upsert
    assert store.count() == 2


def test_inmemory_store_contract():
    run_contract(InMemorySignalStore())


def test_sqlite_store_contract(tmp_path):
    store = SqliteSignalStore(tmp_path / "signals.db")
    run_contract(store)
    store.close()


def test_list_since_filter(tmp_path):
    store = SqliteSignalStore(tmp_path / "signals.db")
    old = NOW - timedelta(hours=2)
    store.save(make_signal(signal_id="old", ingested_at=old))
    store.save(make_signal(signal_id="new", ingested_at=NOW))
    results = store.list(since=NOW - timedelta(hours=1))
    assert [s.signal_id for s in results] == ["new"]
    store.close()


def test_roundtrip_preserves_payload(tmp_path):
    store = SqliteSignalStore(tmp_path / "signals.db")
    original = make_signal()
    store.save(original)
    loaded = store.list()[0]
    assert loaded.model_dump() == original.model_dump()
    store.close()
