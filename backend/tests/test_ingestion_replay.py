from datetime import datetime, timezone

import pytest

from app.core.signal_contract import SourceType
from app.ingestion.adapters import normalize_item
from app.nlp.pipeline import analyze_item
from app.replay import recorder

PUBLISHED = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)


def test_news_adapter_normalizes_headline():
    item = normalize_item(
        SourceType.news,
        {"id": 7, "headline": "Acme misses earnings.", "url": "https://x.test/a"},
    )
    assert item.source_type is SourceType.news
    assert item.external_id == "7"
    assert item.text == "Acme misses earnings."
    assert item.url == "https://x.test/a"


def test_social_adapter_truncates_text():
    item = normalize_item(
        SourceType.social, {"id": "s1", "text": "a" * 600}
    )
    assert len(item.text) == 500


def test_blank_text_rejected():
    with pytest.raises(ValueError):
        normalize_item(SourceType.news, {"id": "n1", "headline": "   "})


def test_missing_id_rejected():
    with pytest.raises(KeyError):
        normalize_item(SourceType.news, {"headline": "Acme misses earnings."})


def test_recorder_roundtrip(tmp_path):
    path = tmp_path / "rec.jsonl"
    sig = analyze_item(
        normalize_item(SourceType.news, {"id": "r1", "headline": "Acme misses earnings."}),
        provenance="replay",
    )
    recorder.record(sig, path)
    loaded = recorder.load(path)
    assert len(loaded) == 1
    assert loaded[0].model_dump() == sig.model_dump()


def test_recorder_rejects_corrupt_lines(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"signal_id": "incomplete"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        recorder.load(path)
