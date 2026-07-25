"""Macro context tool: IHSG historical price stats + recent news."""

from __future__ import annotations

import asyncio
from datetime import date

from agents import function_tool

from app.mcp.news_server import _get_news_impl
from app.modules.ohlcv.service import fetch_candles


def _price_stats(candles) -> dict:
    if not candles:
        return {"error": "no IHSG data available"}

    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    n = len(closes)
    now = closes[-1]

    def pct(days: int) -> float | None:
        if n > days:
            return round((now - closes[-(days + 1)]) / closes[-(days + 1)] * 100, 2)
        return None

    def sma(period: int) -> float | None:
        if n >= period:
            return round(sum(closes[-period:]) / period, 2)
        return None

    ma20, ma50, ma200 = sma(20), sma(50), sma(200)

    ytd_start = next(
        (
            c.close
            for c in candles
            if date.fromtimestamp(c.time).year == date.today().year
        ),
        None,
    )
    ytd_pct = round((now - ytd_start) / ytd_start * 100, 2) if ytd_start else None

    high_52w = round(max(closes[-252:]) if n >= 252 else max(closes), 2)
    low_52w = round(min(closes[-252:]) if n >= 252 else min(closes), 2)

    vol_avg_20 = round(sum(volumes[-21:-1]) / 20, 0) if n >= 21 else None
    vol_ratio = round(volumes[-1] / vol_avg_20, 2) if vol_avg_20 else None

    return {
        "current": round(now, 2),
        "change_1w_pct": pct(5),
        "change_1m_pct": pct(21),
        "change_3m_pct": pct(63),
        "change_ytd_pct": ytd_pct,
        "change_1y_pct": pct(252),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_from_52w_high": round((now - high_52w) / high_52w * 100, 2),
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "above_ma20": (now > ma20) if ma20 else None,
        "above_ma50": (now > ma50) if ma50 else None,
        "above_ma200": (now > ma200) if ma200 else None,
        "volume_ratio_vs_20d": vol_ratio,
        "data_points": n,
    }


@function_tool(
    description_override=(
        "Fetch IHSG (Jakarta Composite Index / JCI) historical price stats and recent "
        "Indonesian market news. Call this for any macro, market-wide, or IHSG question "
        "before writing your response. Returns price level, key MA positions, "
        "period returns, 52-week range, and fresh news about the Indonesian market."
    )
)
async def get_macro_context() -> dict:
    candles, news = await asyncio.gather(
        fetch_candles("^JKSE", days=400),
        _get_news_impl("IHSG JCI Indonesian stock market", max_results=5),
    )
    return {
        "ihsg": _price_stats(candles),
        "news": news,
    }
