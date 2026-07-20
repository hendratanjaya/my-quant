from datetime import date
from typing import Literal

from pydantic import BaseModel

MetricCategory = Literal["valuation", "quality", "growth", "ttm"]


class MetricPercentile(BaseModel):
    """Where the current value sits within its 10-year historical range."""

    metric: str
    category: MetricCategory
    current: float
    percentile: float  # 0–100, share of history below `current`
    min_value: float
    max_value: float


class QuarterPoint(BaseModel):
    period_end: date
    value: float


class QuarterlySeries(BaseModel):
    """A single metric plotted quarter-by-quarter, e.g. OPM, NPM, ROA, ROE."""

    metric: str
    points: list[QuarterPoint]


class PeriodValues(BaseModel):
    """One row of the time-series table — all selected metrics for one quarter."""

    period_end: date
    values: dict[str, float | None]


class FundamentalReport(BaseModel):
    symbol: str
    name: str
    as_of: date
    metrics: list[MetricPercentile]
    quarterly: list[QuarterlySeries]
    time_series: list[PeriodValues]
    comparison: list[PeriodValues]
    reading: str
