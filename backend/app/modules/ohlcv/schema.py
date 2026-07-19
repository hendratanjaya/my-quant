from pydantic import BaseModel


class Candle(BaseModel):
    time: int  # Unix timestamp in seconds (UTC midnight), matches lightweight-charts UTCTimestamp
    open: float
    high: float
    low: float
    close: float
    volume: int
