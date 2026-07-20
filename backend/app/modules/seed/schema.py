from datetime import date, datetime

from pydantic import BaseModel


class FundamentalRowStored(BaseModel):
    period_end: date
    metric: str
    value: float


class SeededTicker(BaseModel):
    """Full record stored in the JSON archive."""

    symbol: str
    seeded_at: datetime
    rows: list[FundamentalRowStored]


class SeededSummary(BaseModel):
    """Lightweight view for the /seed list endpoint (no `rows`)."""

    symbol: str
    seeded_at: datetime
    row_count: int
    period_first: date | None
    period_last: date | None
