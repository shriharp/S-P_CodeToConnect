"""SQLite-backed queue for raw source items awaiting NLP analysis."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.ingestion.adapters import RawSourceItem


class RawItemQueue:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_item_queue (
                provider TEXT NOT NULL,
                external_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at TEXT NOT NULL,
                queued_at TEXT NOT NULL,
                processed_at TEXT,
                last_error TEXT,
                PRIMARY KEY (provider, external_id)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_queue_ready "
            "ON raw_item_queue(status, available_at)"
        )
        self._conn.commit()
        self._lock = Lock()

    def enqueue(self, item: RawSourceItem) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO raw_item_queue
                    (provider, external_id, payload, status, available_at, queued_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (item.provider, item.external_id, item.model_dump_json(), now, now),
            )
            self._conn.commit()
            return cursor.rowcount == 1

    def claim(self, limit: int = 50) -> list[tuple[int, RawSourceItem]]:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT rowid, payload FROM raw_item_queue
                WHERE status = 'pending' AND available_at <= ?
                ORDER BY queued_at ASC LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            for row in rows:
                self._conn.execute(
                    "UPDATE raw_item_queue SET status = 'processing', attempts = attempts + 1 "
                    "WHERE rowid = ?",
                    (row["rowid"],),
                )
            self._conn.commit()
        return [(int(row["rowid"]), RawSourceItem.model_validate_json(row["payload"])) for row in rows]

    def complete(self, rowid: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE raw_item_queue SET status = 'complete', processed_at = ?, last_error = NULL "
                "WHERE rowid = ?",
                (datetime.now(timezone.utc).isoformat(), rowid),
            )
            self._conn.commit()

    def fail(self, rowid: int, error: str, retry_seconds: int = 30) -> None:
        available = datetime.now(timezone.utc).timestamp() + retry_seconds
        available_at = datetime.fromtimestamp(available, timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE raw_item_queue SET status = 'pending', available_at = ?, last_error = ? "
                "WHERE rowid = ?",
                (available_at, error[:500], rowid),
            )
            self._conn.commit()

    def counts(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) AS count FROM raw_item_queue GROUP BY status"
        ).fetchall()
        return {row["status"]: int(row["count"]) for row in rows}

    def close(self) -> None:
        self._conn.close()
