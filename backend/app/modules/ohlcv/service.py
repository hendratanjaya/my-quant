from __future__ import annotations

import asyncio
from datetime import date, timedelta

import yfinance as yf

from app.modules.ohlcv.schema import Candle


def _to_yf_symbol(symbol: str) -> str:
    if symbol.startswith("^"):
        return symbol
    return f"{symbol.upper()}.JK"


def _fetch_sync(yf_symbol: str, start: str, interval: str) -> list[Candle]:
    df = yf.download(
        yf_symbol,
        start=start,
        interval=interval,
        auto_adjust=False,
        progress=False,
        multi_level_index=False,
    )
    if df.empty:  # type: ignore
        return []
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna().reset_index()  # type: ignore
    return [
        Candle(
            time=int(row.Date.value // 1_000_000_000),  # type: ignore
            open=round(float(row.Open), 2),  # type: ignore
            high=round(float(row.High), 2),  # type: ignore
            low=round(float(row.Low), 2),  # type: ignore
            close=round(float(row.Close), 2),  # type: ignore
            volume=int(row.Volume),  # type: ignore
        )
        for row in df.itertuples(index=False)
    ]


async def fetch_candles(
    symbol: str,
    days: int = 730,
    interval: str = "1d",
) -> list[Candle]:
    yf_symbol = _to_yf_symbol(symbol)
    start = (date.today() - timedelta(days=days)).isoformat()
    return await asyncio.to_thread(_fetch_sync, yf_symbol, start, interval)
