"""Durable ingestion state for provider health and source-item cursors."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


class IngestionState:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS source_items (
                provider TEXT NOT NULL,
                external_id TEXT NOT NULL,
                published_at TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (provider, external_id)
            );
            CREATE TABLE IF NOT EXISTS provider_state (
                provider TEXT PRIMARY KEY,
                interval_seconds INTEGER NOT NULL,
                cursor TEXT,
                last_attempt_at TEXT,
                last_success_at TEXT,
                newest_source_at TEXT,
                fetched_count INTEGER NOT NULL DEFAULT 0,
                analyzed_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                retry_after_at TEXT
            );
            """
        )
        self._conn.commit()
        self._lock = Lock()

    def seen(self, provider: str, external_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM source_items WHERE provider = ? AND external_id = ?",
            (provider, external_id),
        ).fetchone()
        return row is not None

    def record_item(self, provider: str, external_id: str, published_at: datetime | None, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO source_items
                    (provider, external_id, published_at, first_seen_at, last_seen_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, external_id) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    status = excluded.status
                """,
                (provider, external_id, published_at.isoformat() if published_at else None, now, now, status),
            )
            self._conn.commit()

    def ensure_provider(self, provider: str, interval_seconds: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO provider_state(provider, interval_seconds) VALUES (?, ?)",
                (provider, interval_seconds),
            )
            self._conn.execute(
                "UPDATE provider_state SET interval_seconds = ? WHERE provider = ?",
                (interval_seconds, provider),
            )
            self._conn.commit()

    def update_provider(self, provider: str, *, interval_seconds: int | None = None,
                        cursor: str | None = None, attempted: bool = False,
                        success: bool = False, fetched: int = 0, analyzed: int = 0,
                        skipped: int = 0, newest_source_at: datetime | None = None,
                        error: str | None = None, retry_after_at: datetime | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO provider_state(provider, interval_seconds)
                VALUES (?, ?)
                """,
                (provider, interval_seconds or 60),
            )
            fields = ["fetched_count = fetched_count + ?", "analyzed_count = analyzed_count + ?", "skipped_count = skipped_count + ?"]
            values: list[object] = [fetched, analyzed, skipped]
            if attempted:
                fields.append("last_attempt_at = ?")
                values.append(now)
            if success:
                fields.append("last_success_at = ?")
                values.append(now)
            if cursor is not None:
                fields.append("cursor = ?")
                values.append(cursor)
            if newest_source_at is not None:
                fields.append("newest_source_at = ?")
                values.append(newest_source_at.isoformat())
            if error is not None:
                fields.extend(["error_count = error_count + 1", "last_error = ?"])
                values.append(error)
            elif success:
                fields.append("last_error = NULL")
            if retry_after_at is not None:
                fields.append("retry_after_at = ?")
                values.append(retry_after_at.isoformat())
            elif success:
                fields.append("retry_after_at = NULL")
            if interval_seconds is not None:
                fields.append("interval_seconds = ?")
                values.append(interval_seconds)
            values.append(provider)
            self._conn.execute(f"UPDATE provider_state SET {', '.join(fields)} WHERE provider = ?", values)
            self._conn.commit()

    def health(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM provider_state ORDER BY provider").fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self._conn.close()
