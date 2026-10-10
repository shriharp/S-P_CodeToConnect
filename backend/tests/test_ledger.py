from datetime import datetime, timedelta, timezone

from app.core.signal_contract import (
    AnalysisStatus,
    EventCategory,
    Provenance,
    QualityFlag,
    RiskSignal,
    SourceType,
)
from app.portfolio.rebalancer import MAX_WEIGHT, Portfolio, rebalance
from app.storage.ledger import (
    InMemoryRebalanceStore,
    SqliteRebalanceStore,
    event_from_result,
)

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def make_signal(
    signal_id,
    ticker="AAPL",
    sentiment=-1.0,
    ingested_at=NOW,
    status=AnalysisStatus.complete,
    company_id="acme",
    summary="Earnings missed estimates.",
):
    return RiskSignal(
        signal_id=signal_id,
        source_item_id="item",
        source_provider="test",
        source_type=SourceType.news,
        ingested_at=ingested_at,
        published_at=ingested_at,
        provenance=Provenance.synthetic,
        company_id=company_id,
        company_name=ticker,
        ticker=ticker,
        event_category=EventCategory.earnings,
        event_summary=summary,
        sentiment_score=sentiment,
        impact_score=None,
        impact_explanation=None,
        evidence_excerpts=[],
        analysis_status=status,
        quality_flags={QualityFlag.insufficient_evidence},
        analyzed_at=ingested_at,
        analysis_method_version="test",
    )


def portfolio():
    return Portfolio(
        weights={"AAPL": 0.2, "MSFT": 0.2, "JPM": 0.2, "XOM": 0.2, "PG": 0.2}
    )


# --- Decision-record correctness -------------------------------------------


def test_one_decision_per_input_signal():
    signals = [
        make_signal("s1", "AAPL", -1.0),
        make_signal("s2", "MSFT", 1.0, company_id="msft"),
        make_signal("s3", "TSLA", -0.5, company_id="tsla"),
    ]
    result = rebalance(portfolio(), signals, NOW)
    assert len(result.decisions) == len(signals)
    assert {d.signal_id for d in result.decisions} == {"s1", "s2", "s3"}


def test_executed_decision_has_final_weight():
    result = rebalance(portfolio(), [make_signal("s1", "AAPL", -1.0)], NOW)
    d = next(x for x in result.decisions if x.signal_id == "s1")
    assert d.decision == "executed"
    assert d.reason is None
    assert d.final_weight is not None
    assert d.original_weight == 0.2
    assert d.final_weight < d.original_weight  # negative sentiment reduced it


def test_skipped_decision_records_reason_and_null_weights():
    result = rebalance(
        portfolio(), [make_signal("s1", "TSLA", -0.5, company_id="tsla")], NOW
    )
    d = result.decisions[0]
    assert d.decision == "skipped"
    assert d.reason == "not_in_portfolio"
    assert d.proposed_weight is None
    assert d.final_weight is None


def test_capped_decision_marked_when_hitting_max():
    p = Portfolio(
        weights={"AAPL": 0.24, "MSFT": 0.19, "JPM": 0.19, "XOM": 0.19, "PG": 0.19}
    )
    result = rebalance(p, [make_signal("s1", "AAPL", 1.0)], NOW)
    d = result.decisions[0]
    assert d.final_weight >= MAX_WEIGHT - 1e-9
    assert d.decision == "capped"
    assert d.reason == "reached_max_weight"


def test_original_weights_preserved_for_reconstruction():
    result = rebalance(portfolio(), [make_signal("s1", "AAPL", -1.0)], NOW)
    assert result.original_weights == portfolio().weights
    assert set(result.proposed_weights) == set(result.original_weights)


def test_policy_version_present():
    result = rebalance(portfolio(), [make_signal("s1")], NOW)
    assert result.policy_version == "module-a-v1"


# --- Portfolio invariants (re-asserted through the new code path) ----------


def test_invariant_weights_sum_to_one_after_ledger():
    signals = [make_signal("s1", "AAPL", -1.0), make_signal("s2", "MSFT", 1.0, company_id="msft")]
    result = rebalance(portfolio(), signals, NOW)
    assert abs(sum(result.proposed_weights.values()) - 1.0) < 1e-9


def test_invariant_no_negative_weights():
    result = rebalance(portfolio(), [make_signal("s1", "AAPL", -1.0)], NOW)
    assert min(result.proposed_weights.values()) >= 0.0


# --- Ledger persistence roundtrip ------------------------------------------


def run_store_contract(store):
    signals = [make_signal("s1", "AAPL", -1.0), make_signal("s2", "MSFT", 1.0, company_id="msft")]
    result = rebalance(portfolio(), signals, NOW)
    store.append(event_from_result(result, "ev1", NOW))
    events = store.list_events()
    assert len(events) == 1
    ev = events[0]
    assert ev.policy_version == result.policy_version
    assert ev.final_weights == result.proposed_weights
    assert ev.original_weights == result.original_weights
    assert len(ev.decisions) == len(result.decisions)
    assert ev.consumed_signal_ids == result.consumed_signal_ids


def test_inmemory_store_contract():
    run_store_contract(InMemoryRebalanceStore())


def test_sqlite_store_contract(tmp_path):
    store = SqliteRebalanceStore(tmp_path / "ledger.db")
    run_store_contract(store)
    store.close()


def test_get_event_by_id(tmp_path):
    store = SqliteRebalanceStore(tmp_path / "ledger.db")
    result = rebalance(portfolio(), [make_signal("s1")], NOW)
    store.append(event_from_result(result, "ev-42", NOW))
    assert store.get_event("ev-42") is not None
    assert store.get_event("missing") is None
    store.close()


def test_weight_history_chronological_and_reconstructable(tmp_path):
    store = SqliteRebalanceStore(tmp_path / "ledger.db")
    # Three sequential rebalances, each starting from the prior result's weights.
    weights = dict(portfolio().weights)
    for i in range(3):
        p = Portfolio(weights=dict(weights))
        result = rebalance(p, [make_signal(f"s{i}", "AAPL", -1.0)], NOW + timedelta(minutes=i))
        store.append(event_from_result(result, f"ev{i}", NOW + timedelta(minutes=i)))
        weights = result.proposed_weights

    history = store.weight_history()
    assert len(history) == 3
    # Chronological order preserved.
    assert [h["event_id"] for h in history] == ["ev0", "ev1", "ev2"]
    # Each row's weights sum to 1 and are reconstructable per ticker.
    for row in history:
        assert abs(sum(row["weights"].values()) - 1.0) < 1e-9
    # Final row matches the last rebalance output exactly.
    assert history[-1]["weights"] == weights
    store.close()
