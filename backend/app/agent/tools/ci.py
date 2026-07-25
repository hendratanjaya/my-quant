"""CI (Chart Investing) framework signal function tool."""

from __future__ import annotations

from agents import function_tool

from app.lib.ci_system import compute
from app.modules.ohlcv.service import fetch_candles


async def _check_ci_impl(symbol: str, days: int = 730) -> dict:
    candles = await fetch_candles(symbol, days)
    return compute(symbol, candles)


@function_tool(
    description_override=(
        "Compute the CI (Chart Investing) framework signal state for an IDX ticker. "
        "Returns whether the stock is currently SUPERKETAT, KETAT, THEONE, or "
        "KAMEHAMEHA, how compressed the MAs are, and historical setup frequency. "
        "You MUST call this before writing any technical analysis or commenting "
        "on entry conditions."
    )
)
async def check_ci(symbol: str, days: int = 730) -> dict:
    """Args: symbol (IDX ticker); days (lookback window, default 730 ~= 2 years)."""
    return await _check_ci_impl(symbol, days)
