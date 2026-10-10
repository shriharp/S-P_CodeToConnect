"""Fetch market data from yfinance and write committed CSVs under /data.

Run ONCE (network required); outputs are committed so the runtime demo is
offline and deterministic. yfinance is Apache-2.0 (license verified 2026-10-09).

Usage:
    cd backend && .venv/bin/python -m scripts.fetch_market_data

Writes:
    /data/market_prices.csv   date,ticker,close   (last ~90 trading days)
    /data/ticker_metadata.csv ticker,company_id,sector,market_cap
"""

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.entities import COMPANIES  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Static sector labels for the 10 mock-index companies (public, well-known).
SECTORS = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "JPM": "Financials",
    "XOM": "Energy",
    "PG": "Consumer Staples",
    "KO": "Consumer Staples",
    "JNJ": "Healthcare",
    "WMT": "Consumer Discretionary",
    "CVX": "Energy",
    "PFE": "Healthcare",
}

LOOKBACK_DAYS = 120  # calendar days -> ~60-90 trading days of price history


def main() -> None:
    import yfinance as yf

    tickers = [c.ticker for c in COMPANIES]
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    end = date.today()
    start = end - timedelta(days=LOOKBACK_DAYS)

    print(f"fetching {len(tickers)} tickers {start} -> {end} ...")
    raw = yf.download(
        tickers,
        start=start.isoformat(),
        end=end.isoformat(),
        auto_adjust=True,
        progress=False,
        group_by="column",
    )

    # --- metadata (market cap) ---
    caps: dict[str, float] = {}
    for t in tickers:
        info = yf.Ticker(t).fast_info
        caps[t] = float(info.market_cap or 0.0)

    with (DATA_DIR / "ticker_metadata.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "company_id", "sector", "market_cap"])
        for c in COMPANIES:
            w.writerow([c.ticker, c.company_id, SECTORS[c.ticker], f"{caps[c.ticker]:.0f}"])

    # --- prices (long format) ---
    closes = raw["Close"]
    rows = 0
    with (DATA_DIR / "market_prices.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "ticker", "close"])
        for d in closes.index:
            day = d.date().isoformat()
            for t in tickers:
                val = closes.loc[d, t]
                if val is not None and val == val:  # not NaN
                    w.writerow([day, t, f"{float(val):.4f}"])
                    rows += 1

    print(f"wrote {rows} price rows + {len(tickers)} metadata rows to {DATA_DIR}")
    print("commit /data so the demo runs offline.")


if __name__ == "__main__":
    main()
