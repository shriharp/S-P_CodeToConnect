from app.core.entities import company_by_ticker, resolve


def test_longest_alias_wins():
    resolutions = resolve("Johnson & Johnson reported earnings.")
    assert len(resolutions) == 1
    assert resolutions[0].company.ticker == "JNJ"
    assert resolutions[0].matched_alias == "johnson & johnson"


def test_short_alias_resolves():
    resolutions = resolve("Pfizer plummeted on the news.")
    assert resolutions[0].company.ticker == "PFE"


def test_multi_company_all_resolved():
    resolutions = resolve("Apple cut revenue while Microsoft won a contract.")
    assert {r.company.ticker for r in resolutions} == {"AAPL", "MSFT"}


def test_same_company_reported_once():
    resolutions = resolve("Apple Inc. and Apple both fell; an Apple unit struggles.")
    assert len(resolutions) == 1


def test_no_match_returns_empty():
    assert resolve("The meeting is on Tuesday.") == []


def test_case_insensitive():
    assert resolve("APPLE reported EARNINGS")[0].company.ticker == "AAPL"


def test_lookup_by_ticker():
    assert company_by_ticker("aapl").name == "Apple Inc."
    assert company_by_ticker("nope") is None


def test_cashtag_resolves():
    resolutions = resolve("$AAPL to the moon, loving $MSFT here")
    assert {r.company.ticker for r in resolutions} == {"AAPL", "MSFT"}


def test_cashtag_and_alias_mix_without_double_count():
    resolutions = resolve("Apple and $JPM both look good")
    assert {r.company.ticker for r in resolutions} == {"AAPL", "JPM"}


def test_unknown_cashtag_ignored():
    # $ZZZZ is not in the registry -> no resolution, no crash.
    assert resolve("$ZZZZ nothing else here") == []
