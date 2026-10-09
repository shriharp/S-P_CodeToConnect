"""Recorded-output replay: serve previously computed signals without inference.

This is execution mode 3 from docs/architecture.md. Replayed signals carry
provenance=replay and their original analysis timestamps; no model or
deterministic scoring runs. Distinct from synthetic fixtures (provenance=
synthetic) and from fresh historical replay (provenance=replay only after
fresh inference over historical text).
"""

import json
from pathlib import Path

from app.core.signal_contract import RiskSignal


def record(signal: RiskSignal, path: Path) -> None:
    """Append one signal to a JSONL recording file."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(signal.model_dump_json() + "\n")


def load(path: Path) -> list[RiskSignal]:
    """Load a recording; every line must be a valid contract signal."""
    signals: list[RiskSignal] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                signals.append(RiskSignal.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"invalid recording at line {line_no}: {exc}") from exc
    return signals
