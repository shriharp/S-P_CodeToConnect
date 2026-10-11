"""Backend-owned live ingestion scheduler."""

import os
import logging
import threading
from datetime import datetime, timezone

from app.ingestion.live_poller import poll_live

logger = logging.getLogger(__name__)

class IngestionScheduler:
    def __init__(self, run_once) -> None:
        self._run_once = run_once
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return os.getenv("INGESTION_SCHEDULER_ENABLED", "false").lower() in {"1", "true", "yes"}

    def start(self) -> None:
        if not self.enabled or self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="risk-ingestion", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        interval = int(os.getenv("INGESTION_INTERVAL_SECONDS", "90"))
        while not self._stop.is_set():
            try:
                self._run_once()
            except Exception:
                logger.exception("Scheduled ingestion cycle failed")
            self._stop.wait(interval)
