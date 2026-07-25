"""CI System (Chart Investing) signal computation.

Pure library — no I/O, no side effects. Takes a list of Candle objects,
returns a typed dict matching the ci tool interface.

Credit: CI System framework by Chart Investing, 2020–2021.
Personal use only.
"""

from __future__ import annotations

from app.modules.ohlcv.schema import Candle


def _sma(closes: list[float], end: int, period: int) -> float:
    """SMA of `period` values ending at index `end` (inclusive)."""
    return sum(closes[end - period + 1 : end + 1]) / period


def compute(symbol: str, candles: list[Candle]) -> dict:
    """Compute CI signals from a list of daily candles.

    Needs at least 20 candles. Returns null signals if data is insufficient.
    """
    if len(candles) < 20:
        return _insufficient(symbol)

    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    n = len(closes)
    last = n - 1
    price = closes[last]

    # ── Moving averages (last bar) ───────────────────────────────────
    ma3 = _sma(closes, last, 3)
    ma5 = _sma(closes, last, 5)
    ma10 = _sma(closes, last, 10)
    ma20 = _sma(closes, last, 20)
    ma50 = _sma(closes, last, 50) if n >= 50 else None
    ma100 = _sma(closes, last, 100) if n >= 100 else None
    ma200 = _sma(closes, last, 200) if n >= 200 else None

    core = [ma3, ma5, ma10, ma20]  # CI uses exactly these four

    # ── CI conditions ────────────────────────────────────────────────
    price_above_all = all(price > ma for ma in core)

    def within_5pct(ma: float) -> bool:
        return (price - ma) / ma <= 0.05

    # SUPERKETAT: above ALL core MAs AND within 5% of ALL
    superketat = price_above_all and all(within_5pct(ma) for ma in core)

    # KETAT: above ALL core MAs AND within 5% of AT LEAST ONE
    ketat = price_above_all and any(within_5pct(ma) for ma in core)

    # ── Volume ──────────────────────────────────────────────────────
    # Ratio of today's volume vs the previous 20 sessions (not including today)
    vol_avg_20 = sum(volumes[-21:-1]) / 20 if n >= 21 else None
    volume_ratio = round(volumes[-1] / vol_avg_20, 2) if vol_avg_20 else None

    # ── Momentum ────────────────────────────────────────────────────
    momentum_5d = (
        round((closes[-1] - closes[-6]) / closes[-6] * 100, 2) if n >= 6 else None
    )
    bullish = momentum_5d is not None and momentum_5d > 0

    # ── Composite signals ────────────────────────────────────────────
    in_ci = ketat or superketat
    theone = in_ci and volume_ratio is not None and volume_ratio > 1.5 and bullish
    kamehameha = in_ci and volume_ratio is not None and volume_ratio >= 3.0

    # ── MA spread (compression) ──────────────────────────────────────
    ma_spread_pct = round((max(core) - min(core)) / min(core) * 100, 2)

    # ── Historical setup frequency ───────────────────────────────────
    setup_frequency_pct = _setup_frequency(closes)

    return {
        "ticker": symbol.upper(),
        "price": price,
        "ma_values": {
            "ma3": round(ma3, 2),
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "ma50": round(ma50, 2) if ma50 is not None else None,
            "ma100": round(ma100, 2) if ma100 is not None else None,
            "ma200": round(ma200, 2) if ma200 is not None else None,
        },
        "ma_spread_pct": ma_spread_pct,
        "volume_ratio": volume_ratio,
        "ci_signals": {
            "superketat": superketat,
            "ketat": ketat,
            "theone": theone,
            "kamehameha": kamehameha,
        },
        "setup_frequency_pct": setup_frequency_pct,
        "momentum_5d_pct": momentum_5d,
    }


def _setup_frequency(closes: list[float]) -> float | None:
    """% of historical days that qualified as KETAT or SUPERKETAT."""
    if len(closes) < 21:
        return None

    setup_days = 0
    total_days = 0

    for i in range(20, len(closes)):
        p = closes[i]
        m3 = sum(closes[i - 2 : i + 1]) / 3
        m5 = sum(closes[i - 4 : i + 1]) / 5
        m10 = sum(closes[i - 9 : i + 1]) / 10
        m20 = sum(closes[i - 19 : i + 1]) / 20

        above_all = p > m3 and p > m5 and p > m10 and p > m20
        if above_all and any((p - ma) / ma <= 0.05 for ma in [m3, m5, m10, m20]):
            setup_days += 1
        total_days += 1

    return round(setup_days / total_days * 100, 1)


def _insufficient(symbol: str) -> dict:
    return {
        "ticker": symbol.upper(),
        "price": None,
        "ma_values": {
            k: None for k in ["ma3", "ma5", "ma10", "ma20", "ma50", "ma100", "ma200"]
        },
        "ma_spread_pct": None,
        "volume_ratio": None,
        "ci_signals": {
            "superketat": False,
            "ketat": False,
            "theone": False,
            "kamehameha": False,
        },
        "setup_frequency_pct": None,
        "momentum_5d_pct": None,
    }
