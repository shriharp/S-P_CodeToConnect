"""Generate a larger deterministic demo replay dataset.

Expands data/demo_news.jsonl from ~15 hand-written items to a few dozen
varied items across all 10 mock-index tickers, mixing event categories and
sentiment directions so the Weight Evolution Timeline shows meaningful,
reproducible movement (not a flat line). Deterministic via fixed seed.

This is committed data used by the offline demo replay — clearly labeled
provenance=replay at runtime, never presented as live inference.
"""

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "demo_news.jsonl"

COMPANIES = [
    ("Apple", "AAPL"), ("Microsoft", "MSFT"), ("JPMorgan", "JPM"),
    ("Exxon Mobil", "XOM"), ("Procter & Gamble", "PG"), ("Coca-Cola", "KO"),
    ("Johnson & Johnson", "JNJ"), ("Walmart", "WMT"),
    ("Chevron", "CVX"), ("Pfizer", "PFE"),
]

# (template, event flavour) — flavour drives which cues appear.
ITEMS = [
    ("{c} cut revenue guidance after a factory shutdown disrupted production.", "neg"),
    ("{c} beat quarterly earnings estimates and raised its full-year guidance.", "pos"),
    ("A lawsuit alleges {c} misled investors over its accounting.", "neg"),
    ("{c} won a major cloud contract, lifting its outlook.", "pos"),
    ("Credit rating agencies downgraded {c} debt on rising losses.", "neg"),
    ("{c} unveiled a new product line at its annual event.", "pos"),
    ("{c} signed a multi-year supply partnership with a rival.", "pos"),
    ("A recall affected thousands of {c} products after a defect.", "neg"),
    ("{c} posted record profit, beating analyst expectations.", "pos"),
    ("Regulators fined {c} over compliance failures.", "neg"),
    ("{c} announced a dividend increase alongside strong results.", "pos"),
    ("An outage disrupted {c} ordering systems for hours.", "neg"),
    ("{c} agreed to acquire a smaller competitor in a cash deal.", "pos"),
    ("Investors sold off {c} shares after a profit warning.", "neg"),
    ("{c} raised its dividend after a resilient quarter.", "pos"),
    ("A supplier dispute disrupted {c} assembly lines.", "neg"),
    ("{c} launched a new subscription service for its platform.", "pos"),
    ("{c} missed revenue expectations amid weak demand.", "neg"),
    ("{c} entered a joint venture to develop battery technology.", "pos"),
    ("A cyberattack took {c} systems offline, disrupting orders.", "neg"),
]


def main(count: int = 40) -> None:
    random.seed(7)
    rows = []
    for i in range(count):
        name, ticker = COMPANIES[i % len(COMPANIES)]
        template, _flavour = ITEMS[i % len(ITEMS)]
        text = template.format(c=name)
        # Stagger published_at across several days so the timeline is spread out.
        day = 1 + (i % 10)
        hour = 8 + (i * 2) % 10
        published = f"2026-10-{day:02d}T{hour:02d}:00:00Z"
        rows.append({"id": f"demo-{i+1:02d}", "published_at": published, "text": text})
    # Deterministic order by published time.
    rows.sort(key=lambda r: r["published_at"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} demo replay items -> {OUT}")


if __name__ == "__main__":
    main()
