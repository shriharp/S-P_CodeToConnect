"""Signal persistence: SQLite-backed repository behind a swappable interface.

Uses the Python stdlib sqlite3 (no new dependencies). The repository ABC is the
seam for a future Postgres/etc. backend; callers depend only on SignalStore.
Concurrency: WAL mode, one writer; adequate for the demo's single-process
FastAPI server. A connection pool/queue layer is added only when measured
throughput requires it (docs/architecture.md).
"""

import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from app.core.signal_contract import RiskSignal


class SignalStore(ABC):
    """Persistence seam for analyzed signals."""

    @abstractmethod
    def save(self, signal: RiskSignal) -> None: ...

    @abstractmethod
    def list(
        self,
        ticker: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[RiskSignal]: ...

    @abstractmethod
    def count(self) -> int: ...


class SqliteSignalStore(SignalStore):
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                ticker TEXT,
                ingested_at TEXT NOT NULL,
                provenance TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_ingested ON signals(ingested_at)"
        )
        self._conn.commit()

    def save(self, signal: RiskSignal) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO signals
                (signal_id, ticker, ingested_at, provenance, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                signal.signal_id,
                signal.ticker,
                signal.ingested_at.isoformat(),
                signal.provenance.value,
                signal.model_dump_json(),
            ),
        )
        self._conn.commit()

    def list(
        self,
        ticker: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[RiskSignal]:
        query = "SELECT payload FROM signals"
        clauses: list[str] = []
        params: list[object] = []
        if ticker:
            clauses.append("ticker = ?")
            params.append(ticker.upper())
        if since:
            clauses.append("ingested_at >= ?")
            params.append(since.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY ingested_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [RiskSignal.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM signals").fetchone()
        return int(row[0])

    def close(self) -> None:
        self._conn.close()


class InMemorySignalStore(SignalStore):
    """Process-local store for tests and ephemeral runs."""

    def __init__(self) -> None:
        self._signals: dict[str, RiskSignal] = {}

    def save(self, signal: RiskSignal) -> None:
        self._signals[signal.signal_id] = signal

    def list(
        self,
        ticker: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[RiskSignal]:
        out = [
            s
            for s in self._signals.values()
            if (ticker is None or s.ticker == ticker.upper())
            and (since is None or s.ingested_at >= since)
        ]
        out.sort(key=lambda s: s.ingested_at, reverse=True)
        return out[:limit]

    def count(self) -> int:
        return len(self._signals)
