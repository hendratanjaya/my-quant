from fastapi import APIRouter, HTTPException, Query

from app.modules.ohlcv.schema import Candle
from app.modules.ohlcv.service import fetch_candles

router = APIRouter(prefix="/api/ohlcv", tags=["ohlcv"])


@router.get("/{symbol}", response_model=list[Candle])
async def get_ohlcv(
    symbol: str,
    days: int = Query(default=730, ge=1, le=3650),
    interval: str = Query(default="1d", pattern="^(1d|1wk|1mo)$"),
) -> list[Candle]:
    try:
        candles = await fetch_candles(symbol, days, interval)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"yfinance error: {exc}") from exc

    if not candles:
        raise HTTPException(status_code=404, detail=f"No data found for '{symbol}'")

    return candles
