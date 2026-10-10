"""Deterministic demo replay: committed news -> signals -> rebalance sequence.

Runs the committed /data/demo_news.jsonl through the real pipeline and
rebalancer, producing a reproducible weight-history sequence with no network
and no live inference timing. This is the demo backbone: a judge can watch the
full pipeline (text -> company signals -> policy-gated rebalance -> weight
timeline) dependably, independent of whatever news breaks during the pitch.

Provenance is labeled replay (historical text, fresh inference) — distinct from
live inference and from synthetic fixtures, per AGENTS.md.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.entities import resolve
from app.core.signal_contract import Provenance, SourceType
from app.ingestion.adapters import RawSourceItem
from app.nlp.pipeline import analyze_item
from app.portfolio.rebalancer import Portfolio, RebalanceResult, rebalance

DEMO_NEWS = Path(__file__).resolve().parents[3] / "data" / "demo_news.jsonl"


def load_demo_items(path: Path = DEMO_NEWS) -> list[dict]:
    """Load the committed demo news items, ordered by published_at."""
    if not path.exists():
        raise FileNotFoundError(f"demo dataset missing: {path}")
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    items.sort(key=lambda x: x["published_at"])
    return items


def replay(
    initial_weights: dict[str, float] | None = None,
    sentiment_backend: str = "lexicon",
    path: Path = DEMO_NEWS,
) -> list[dict]:
    """Replay the demo dataset through pipeline + rebalancer deterministically.

    Returns a chronological list of steps, one per news item:
      {item_id, published_at, signals, decision_event}

    Each step rebalances the portfolio carrying forward the prior step's final
    weights, so the sequence reconstructs the weight-evolution timeline.
    """
    from app.portfolio.demo import demo_portfolio

    portfolio = (
        Portfolio(weights=dict(initial_weights))
        if initial_weights is not None
        else demo_portfolio()
    )

    steps: list[dict] = []
    for item in load_demo_items(path):
        published = datetime.fromisoformat(
            item["published_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        raw = RawSourceItem(
            provider="demo-replay",
            source_type=SourceType.news,
            external_id=item["id"],
            text=item["text"],
            published_at=published,
        )
        signals = analyze_item(
            raw,
            provenance=Provenance.replay.value,
            sentiment_backend=sentiment_backend,
            ingested_at=published,
        )
        # Only signals whose companies are in the index drive the rebalance;
        # unresolved/out-of-index signals are still returned for inspection.
        result: RebalanceResult = rebalance(portfolio, signals, published)
        portfolio = Portfolio(weights=dict(result.proposed_weights))
        steps.append(
            {
                "item_id": item["id"],
                "published_at": item["published_at"],
                "signals": signals,
                "decision_event": result,
            }
        )
    return steps


def weight_timeline(steps: list[dict]) -> list[dict]:
    """Extract the per-step final weights for the evolution chart."""
    return [
        {
            "item_id": s["item_id"],
            "timestamp": s["published_at"],
            "weights": s["decision_event"].proposed_weights,
        }
        for s in steps
    ]
