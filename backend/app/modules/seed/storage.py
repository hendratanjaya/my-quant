"""JSON-file storage for seeded fundamentals. Dev-mode only; swapped for SQLite later."""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.seed.schema import SeededTicker

DATA_DIR = Path("data")
SEED_FILE = DATA_DIR / "seeded.json"


def load() -> dict[str, SeededTicker]:
    """Read the archive. Empty dict if the file doesn't exist yet."""
    if not SEED_FILE.exists():
        return {}
    with SEED_FILE.open() as f:
        raw = json.load(f)
    return {symbol: SeededTicker.model_validate(payload) for symbol, payload in raw.items()}


def save(store: dict[str, SeededTicker]) -> None:
    """Atomic write: dump to a temp file, then rename."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {symbol: ticker.model_dump(mode="json") for symbol, ticker in store.items()}
    tmp = SEED_FILE.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(SEED_FILE)
