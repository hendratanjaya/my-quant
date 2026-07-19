import asyncio
from datetime import date, timedelta

import yfinance as yf
from fastapi import APIRouter, HTTPException, Query

from app.modules.ohlcv.schema import Candle

router = APIRouter(prefix="/api/ohlcv", tags=["ohlcv"])


def _to_yf_symbol(symbol: str) -> str:
    """^JKSE passes through; everything else gets .JK appended."""
    if symbol.startswith("^"):
        return symbol
    return f"{symbol.upper()}.JK"


def _fetch(yf_symbol: str, start: str, interval: str) -> list[Candle]:
    df = yf.download(
        yf_symbol,
        start=start,
        interval=interval,
        auto_adjust=True,
        progress=False,
        multi_level_index=False,
    )

    if df.empty:  # type: ignore
        return []

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()  # type: ignore
    df = df.reset_index()

    return [
        Candle(
            # pandas Timestamp nanoseconds → seconds, always UTC midnight for daily data
            time=int(row.Date.value // 1_000_000_000),  # type: ignore
            open=round(float(row.Open), 2),  # type: ignore
            high=round(float(row.High), 2),  # type: ignore
            low=round(float(row.Low), 2),  # type: ignore
            close=round(float(row.Close), 2),  # type: ignore
            volume=int(row.Volume),  # type: ignore
        )
        for row in df.itertuples(index=False)
    ]


@router.get("/{symbol}", response_model=list[Candle])
async def get_ohlcv(
    symbol: str,
    days: int = Query(default=730, ge=1, le=3650),
    interval: str = Query(default="1d", pattern="^(1d|1wk|1mo)$"),
) -> list[Candle]:
    yf_symbol = _to_yf_symbol(symbol)
    start = (date.today() - timedelta(days=days)).isoformat()

    try:
        candles = await asyncio.to_thread(_fetch, yf_symbol, start, interval)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"yfinance error: {exc}"
        ) from exc

    if not candles:
        raise HTTPException(
            status_code=404, detail=f"No data found for '{symbol}'"
        )

    return candles
