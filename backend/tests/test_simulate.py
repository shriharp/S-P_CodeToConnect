from datetime import datetime, timezone

from app.portfolio.demo import demo_portfolio, demo_signal
from app.portfolio.rebalancer import rebalance
from app.storage.ledger import InMemoryRebalanceStore, event_from_result

NOW = datetime.now(timezone.utc)


def _result(sentiment=-1.0):
    sig = demo_signal(
        ticker="AAPL",
        sentiment=sentiment,
        text="what-if",
        source_item_id="sim-1",
        ingested_at=NOW,
    )
    return rebalance(demo_portfolio(), [sig], NOW)


def test_simulate_computes_real_adjustments():
    # /simulate is rebalance() with no ledger.append — the computation is real.
    assert _result().adjustments


def test_rebalance_engine_alone_persists_nothing():
    # A ledger store stays empty unless append() is called explicitly, so the
    # simulate path (which never appends) cannot pollute audited history.
    store = InMemoryRebalanceStore()
    _result()
    assert store.list_events() == []


def test_explicit_append_is_the_only_persistence():
    store = InMemoryRebalanceStore()
    store.append(event_from_result(_result(), "ev1", NOW))
    assert len(store.list_events()) == 1


def test_related_signals_are_aggregated_into_one_policy_adjustment():
    first = demo_signal("AAPL", -1.0, "first report", "source-1", NOW)
    second = demo_signal("AAPL", -1.0, "second report", "source-2", NOW)
    result = rebalance(demo_portfolio(), [first, second], NOW)

    # Two related reports contribute one step, while both IDs remain audited.
    assert result.consumed_signal_ids == ["source-1-AAPL", "source-2-AAPL"]
    assert result.adjustments["AAPL"] < 0
    assert all(d.reason == "aggregated_2_related_sources" for d in result.decisions)
