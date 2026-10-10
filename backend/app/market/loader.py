"""Offline market-data loader: reads committed CSVs, never touches the network.

The demo must run without live connectivity (AGENTS.md, problem statement). CSVs
are fetched once by scripts/fetch_market_data.py and committed under /data. This
loader only reads them, so runtime is deterministic and offline.

Data model:
- prices CSV: date,ticker,close  (long format, one row per ticker per day)
- metadata CSV: ticker,company_id,sector,market_cap  (for seed weights + sector)
"""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Repo-root /data (three levels up from backend/app/market/loader.py).
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
PRICES_CSV = DATA_DIR / "market_prices.csv"
METADATA_CSV = DATA_DIR / "ticker_metadata.csv"


@dataclass(frozen=True)
class TickerMeta:
    ticker: str
    company_id: str
    sector: str
    market_cap: float


def load_metadata(path: Path = METADATA_CSV) -> list[TickerMeta]:
    """Load per-ticker metadata (sector + market cap for seed weights)."""
    if not path.exists():
        raise FileNotFoundError(
            f"metadata CSV missing: {path}. Run scripts/fetch_market_data.py "
            "once (network required) to populate /data."
        )
    out: list[TickerMeta] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.append(
                TickerMeta(
                    ticker=row["ticker"].upper(),
                    company_id=row["company_id"],
                    sector=row["sector"],
                    market_cap=float(row["market_cap"]),
                )
            )
    return out


def load_prices(path: Path = PRICES_CSV) -> dict[str, dict[date, float]]:
    """Load close prices as {ticker: {date: close}}.

    Raises FileNotFoundError when absent so callers fail loudly rather than
    fabricating prices (AGENTS.md: never fabricate data).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"prices CSV missing: {path}. Run scripts/fetch_market_data.py "
            "once (network required) to populate /data."
        )
    prices: dict[str, dict[date, float]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ticker = row["ticker"].upper()
            d = date.fromisoformat(row["date"])
            prices.setdefault(ticker, {})[d] = float(row["close"])
    return prices


def market_cap_weights(metas: list[TickerMeta] | None = None) -> dict[str, float]:
    """Derive initial portfolio weights from real market caps, normalized to 1.

    Market-cap weighting is the defensible, non-fabricated seed: larger companies
    get larger baseline weights. Falls back to equal weight only if caps are
    missing/zero (never silently — caller can detect via sum check).
    """
    if metas is None:
        metas = load_metadata()
    total = sum(m.market_cap for m in metas)
    if total <= 0:
        raise ValueError("market caps must sum to a positive value")
    return {m.ticker: m.market_cap / total for m in metas}
