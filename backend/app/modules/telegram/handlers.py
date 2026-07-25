"""Command handlers."""

from __future__ import annotations

_VALID_SIGNALS = {"ketat", "superketat", "theone", "kamehameha"}


def handle_screen_args(args: list[str]) -> tuple[list[str], str | None]:
    """Validate args. Returns (signals, error_message)."""
    signals = [a.lower() for a in args if a.lower() in _VALID_SIGNALS]
    if not signals:
        valid = ", ".join(sorted(_VALID_SIGNALS))
        return [], f"Specify at least one signal: {valid}"
    return signals, None
