"""Rebalance decision ledger: auditable, append-only event store.

Persists one row per rebalance event with original weights, final weights, the
full per-signal decision list, consumed signal IDs, timestamps, and the policy
version. Supports reconstructing the portfolio's weight history over time
(weight-evolution timeline) and per-event drill-down.

Mirrors the SqliteSignalStore pattern: stdlib sqlite3, WAL, swappable behind an
ABC. Decisions are stored as JSON (the DecisionRecord list) so the schema stays
stable while the ledger remains human-inspectable.
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from app.portfolio.rebalancer import DecisionRecord, RebalanceResult


@dataclass
class RebalanceEvent:
    """One persisted rebalance, ready for audit and timeline rendering."""

    event_id: str
    timestamp: datetime
    policy_version: str
    original_weights: dict[str, float]
    final_weights: dict[str, float]
    adjustments: dict[str, float]
    decisions: list[DecisionRecord] = field(default_factory=list)
    consumed_signal_ids: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    disclaimer: str = ""


class RebalanceStore(ABC):
    """Persistence seam for the rebalance decision ledger."""

    @abstractmethod
    def append(self, event: RebalanceEvent) -> None: ...

    @abstractmethod
    def list_events(self, limit: int = 100) -> list[RebalanceEvent]: ...

    @abstractmethod
    def get_event(self, event_id: str) -> RebalanceEvent | None: ...

    @abstractmethod
    def weight_history(self) -> list[dict]:
        """Chronological per-ticker weight series for the evolution timeline.

        Each row: {event_id, timestamp, weights: {ticker: weight}}.
        """


def event_from_result(
    result: RebalanceResult, event_id: str, timestamp: datetime
) -> RebalanceEvent:
    """Build a persistable RebalanceEvent from a RebalanceResult."""
    return RebalanceEvent(
        event_id=event_id,
        timestamp=timestamp,
        policy_version=result.policy_version,
        original_weights=result.original_weights,
        final_weights=result.proposed_weights,
        adjustments=result.adjustments,
        decisions=result.decisions,
        consumed_signal_ids=result.consumed_signal_ids,
        skipped=result.skipped,
        disclaimer=result.disclaimer,
    )


def _serialize(event: RebalanceEvent) -> tuple:
    decisions = [asdict(d) for d in event.decisions]
    return (
        event.event_id,
        event.timestamp.isoformat(),
        event.policy_version,
        json.dumps(event.original_weights, sort_keys=True),
        json.dumps(event.final_weights, sort_keys=True),
        json.dumps(event.adjustments, sort_keys=True),
        json.dumps(decisions),
        json.dumps(event.consumed_signal_ids),
        json.dumps(event.skipped),
        event.disclaimer,
    )


def _deserialize(row: tuple) -> RebalanceEvent:
    return RebalanceEvent(
        event_id=row[0],
        timestamp=datetime.fromisoformat(row[1]),
        policy_version=row[2],
        original_weights=json.loads(row[3]),
        final_weights=json.loads(row[4]),
        adjustments=json.loads(row[5]),
        decisions=[DecisionRecord(**d) for d in json.loads(row[6])],
        consumed_signal_ids=json.loads(row[7]),
        skipped=json.loads(row[8]),
        disclaimer=row[9],
    )


_SCHEMA = """
CREATE TABLE IF NOT EXISTS rebalance_events (
    event_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    original_weights TEXT NOT NULL,
    final_weights TEXT NOT NULL,
    adjustments TEXT NOT NULL,
    decisions TEXT NOT NULL,
    consumed_signal_ids TEXT NOT NULL,
    skipped TEXT NOT NULL,
    disclaimer TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rebalance_ts ON rebalance_events(timestamp);
"""


class SqliteRebalanceStore(RebalanceStore):
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append(self, event: RebalanceEvent) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO rebalance_events
                (event_id, timestamp, policy_version, original_weights,
                 final_weights, adjustments, decisions, consumed_signal_ids,
                 skipped, disclaimer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _serialize(event),
        )
        self._conn.commit()

    def list_events(self, limit: int = 100) -> list[RebalanceEvent]:
        rows = self._conn.execute(
            "SELECT * FROM rebalance_events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_deserialize(r) for r in rows]

    def get_event(self, event_id: str) -> RebalanceEvent | None:
        row = self._conn.execute(
            "SELECT * FROM rebalance_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return _deserialize(row) if row else None

    def weight_history(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT event_id, timestamp, final_weights FROM rebalance_events "
            "ORDER BY timestamp ASC"
        ).fetchall()
        return [
            {
                "event_id": r[0],
                "timestamp": r[1],
                "weights": json.loads(r[2]),
            }
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()


class InMemoryRebalanceStore(RebalanceStore):
    """Process-local ledger for tests and ephemeral runs."""

    def __init__(self) -> None:
        self._events: dict[str, RebalanceEvent] = {}

    def append(self, event: RebalanceEvent) -> None:
        self._events[event.event_id] = event

    def list_events(self, limit: int = 100) -> list[RebalanceEvent]:
        events = sorted(
            self._events.values(), key=lambda e: e.timestamp, reverse=True
        )
        return events[:limit]

    def get_event(self, event_id: str) -> RebalanceEvent | None:
        return self._events.get(event_id)

    def weight_history(self) -> list[dict]:
        events = sorted(self._events.values(), key=lambda e: e.timestamp)
        return [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "weights": e.final_weights,
            }
            for e in events
        ]
