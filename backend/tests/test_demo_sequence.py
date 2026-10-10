from app.replay.demo_sequence import load_demo_items, replay, weight_timeline


def test_load_demo_items_sorted():
    items = load_demo_items()
    assert len(items) >= 10
    times = [i["published_at"] for i in items]
    assert times == sorted(times)


def test_replay_steps_match_items():
    items = load_demo_items()
    steps = replay()
    assert len(steps) == len(items)
    assert [s["item_id"] for s in steps] == [i["id"] for i in items]


def test_replay_is_deterministic():
    a = replay()
    b = replay()
    wa = weight_timeline(a)[-1]["weights"]
    wb = weight_timeline(b)[-1]["weights"]
    for ticker in wa:
        assert abs(wa[ticker] - wb[ticker]) < 1e-9


def test_replay_weights_sum_to_one_at_every_step():
    for row in weight_timeline(replay()):
        assert abs(sum(row["weights"].values()) - 1.0) < 1e-9


def test_replay_respects_cap_at_every_step():
    from app.portfolio.rebalancer import MAX_WEIGHT

    for row in weight_timeline(replay()):
        assert max(row["weights"].values()) <= MAX_WEIGHT + 1e-9


def test_replay_drives_weight_movement():
    # The sequence contains directional news, so at least one ticker's weight
    # must move off its starting value across the run.
    rows = weight_timeline(replay())
    first, last = rows[0]["weights"], rows[-1]["weights"]
    assert any(abs(first[t] - last[t]) > 1e-6 for t in first)


def test_replay_labels_provenance_replay():
    steps = replay()
    for s in steps:
        for sig in s["signals"]:
            assert sig.provenance.value == "replay"


def test_replay_signals_carry_ingested_at_not_wallclock():
    # Freshness must evaluate against event time, so ingested_at == published.
    steps = replay()
    for s in steps:
        for sig in s["signals"]:
            assert sig.ingested_at.isoformat()[:10] == s["published_at"][:10]
