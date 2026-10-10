import pytest

from app.nlp.sentiment_model import available

pytestmark = pytest.mark.skipif(
    not available(), reason="transformers not installed"
)


def test_model_backend_scores_and_labels_method():
    from app.nlp.pipeline import analyze_item
    from app.ingestion.adapters import RawSourceItem
    from app.core.signal_contract import SourceType

    item = RawSourceItem(
        provider="test",
        source_type=SourceType.news,
        external_id="m1",
        text="Apple cut revenue guidance after a factory shutdown.",
    )
    sig = analyze_item(item, provenance="synthetic", sentiment_backend="model")[0]
    assert sig.sentiment_score is not None and sig.sentiment_score < 0
    # Method version reports both the sentiment and event backends in use.
    assert sig.analysis_method_version.startswith("distilroberta-fin-0.1")


def test_model_neutral_maps_to_zero():
    from app.nlp.sentiment_model import score_sentiment_model

    score = score_sentiment_model("Walmart named a new head of its grocery division.")
    assert score == 0.0
