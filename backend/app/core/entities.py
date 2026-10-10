"""Company entity resolution: map names/aliases in text to ticker + company_id.

Deterministic longest-alias matching against a curated registry. Deliberately
conservative: no fuzzy matching, no fabricated identities. Swappable for a
model/entity-linker backend behind the same resolve() interface later.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Company:
    company_id: str
    name: str
    ticker: str
    aliases: tuple[str, ...]


COMPANIES: tuple[Company, ...] = (
    Company("apple", "Apple Inc.", "AAPL", ("apple inc", "apple")),
    Company("microsoft", "Microsoft Corp.", "MSFT", ("microsoft corp", "microsoft")),
    Company("jpmorgan", "JPMorgan Chase", "JPM", ("jpmorgan chase", "jpmorgan", "jp morgan")),
    Company("exxon", "Exxon Mobil", "XOM", ("exxon mobil", "exxonmobil", "exxon")),
    Company("procter-gamble", "Procter & Gamble", "PG", ("procter & gamble", "procter and gamble", "p&g")),
    Company("coca-cola", "Coca-Cola Co", "KO", ("coca-cola", "coca cola", "coke")),
    Company("jnj", "Johnson & Johnson", "JNJ", ("johnson & johnson", "johnson and johnson", "j&j")),
    Company("walmart", "Walmart Inc.", "WMT", ("walmart inc", "walmart")),
    Company("chevron", "Chevron Corp.", "CVX", ("chevron corp", "chevron")),
    Company("pfizer", "Pfizer Inc.", "PFE", ("pfizer inc", "pfizer")),
)

# Longest alias first so "acme corp" wins over "acme".
_ALIAS_INDEX: tuple[tuple[str, Company], ...] = tuple(
    sorted(
        ((alias, company) for company in COMPANIES for alias in company.aliases),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
)


@dataclass(frozen=True)
class Resolution:
    company: Company
    matched_alias: str


def resolve(text: str) -> list[Resolution]:
    """Return every distinct company resolved in text, longest-alias wins.

    Resolves both plain aliases ("Apple") and cashtags ("$AAPL") — cashtags are
    how StockTwits/social posts reference tickers. A company is reported once
    even if matched multiple ways.
    """
    lower = text.lower()
    found: dict[str, Resolution] = {}
    consumed = lower  # track which spans matched to avoid substring double-count

    # Cashtags first: $AAPL -> AAPL company. Word-boundary safe, dedup by company.
    for match in re.finditer(r"\$([A-Za-z]{1,5})\b", text):
        company = company_by_ticker(match.group(1))
        if company is not None and company.company_id not in found:
            found[company.company_id] = Resolution(
                company=company, matched_alias=match.group(0).lower()
            )
            # blank out so alias matching doesn't double-count the same span
            consumed = (
                consumed[: match.start()] + " " * (match.end() - match.start())
                + consumed[match.end():]
            )

    for alias, company in _ALIAS_INDEX:
        if company.company_id in found:
            continue
        idx = consumed.find(alias)
        if idx == -1:
            continue
        found[company.company_id] = Resolution(company=company, matched_alias=alias)
        # blank out the span so shorter aliases inside it cannot re-match
        consumed = consumed[:idx] + " " * len(alias) + consumed[idx + len(alias):]
    return list(found.values())


def company_by_ticker(ticker: str) -> Company | None:
    for company in COMPANIES:
        if company.ticker == ticker.upper():
            return company
    return None
