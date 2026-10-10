import pytest

from app.core.signal_contract import EventCategory, Provenance, SourceType
from app.ingestion.adapters import RawSourceItem
from app.nlp.event_model import available

pytestmark = pytest.mark.skipif(not available(), reason="transformers not installed")


def _analyze(text, event_backend):
    item = RawSourceItem(
        provider="test",
        source_type=SourceType.news,
        external_id="t-1",
        text=text,
    )
    from app.nlp.pipeline import analyze_item

    return analyze_item(item, provenance="synthetic", event_backend=event_backend)[0]


def test_model_backend_returns_valid_category():
    sig = _analyze(
        "The central bank raised interest rates to combat inflation.",
        event_backend="model",
    )
    assert isinstance(sig.event_category, EventCategory)
    # zero-shot NLI should catch this macro case the keyword table can miss
    assert sig.event_category is EventCategory.macroeconomic
    assert "zero-shot-nli" in sig.analysis_method_version


def test_model_backend_abstains_on_chatter():
    sig = _analyze("To the moon 🚀🚀", event_backend="model")
    assert sig.event_category is EventCategory.unknown


def test_keyword_backend_unchanged():
    sig = _analyze(
        "The company filed for bankruptcy protection.",
        event_backend="keyword",
    )
    assert sig.event_category is EventCategory.credit_event
    assert "zero-shot-nli" not in sig.analysis_method_version


def test_keyword_is_default():
    sig = _analyze("The company filed for bankruptcy protection.", event_backend="keyword")
    assert "zero-shot-nli" not in sig.analysis_method_version


def test_event_eval_cases_exist():
    # The eval set is what makes the benchmark defensible.
    from app.nlp.event_eval_cases import EVENT_EVAL_CASES

    assert len(EVENT_EVAL_CASES) >= 30
    categories = {gold for _, gold in EVENT_EVAL_CASES}
    assert "unknown" in categories  # includes abstention cases
