"""Market data MCP server — stdio transport, spawned as a subprocess by the agent orchestrator."""

from __future__ import annotations

from app.lib.ci_system import _sma
from app.modules.ohlcv.service import fetch_candles
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("market-data-mcp")

_MA_PERIODS = [3, 5, 10, 20, 50, 100, 200]


@mcp.tool(
    description=(
        "Call this when you need to describe recent price action or candle patterns for a ticker. "
        "Returns the last N candles (open, high, low, close, volume). "
        "Use before writing any commentary on what the price has been doing recently."
    )
)
async def get_ohlcv(symbol: str, count: int = 10) -> list[dict]:
    """
    Args:
        symbol: IDX ticker, e.g. 'BBRI'
        count:  number of recent candles to return (default 10)
    """
    candles = await fetch_candles(symbol, days=max(count * 2, 60))
    recent = candles[-count:]
    return [
        {
            "date": c.time,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in recent
    ]


@mcp.tool(
    description=(
        "Call this when you need the current MA values for a ticker to fill the "
        "moving_averages section of your analysis. "
        "Returns MA3/5/10/20/50/100/200 and whether price is above each one."
    )
)
async def get_ma(symbol: str) -> dict:
    """
    Args:
        symbol: IDX ticker, e.g. 'BBRI'
    """
    candles = await fetch_candles(symbol, days=730)
    closes = [c.close for c in candles]
    n = len(closes)
    price = closes[-1]

    ma_values = {}
    for period in _MA_PERIODS:
        if n >= period:
            value = round(_sma(closes, n - 1, period), 2)
            ma_values[f"ma{period}"] = {
                "value": value,
                "price_above": price > value,
            }
        else:
            ma_values[f"ma{period}"] = None

    return {"ticker": symbol.upper(), "price": price, "ma": ma_values}


if __name__ == "__main__":
    mcp.run()
