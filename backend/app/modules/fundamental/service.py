"""Build a fundamental report from the database.

Reads FundamentalDataRow records for a symbol, groups by metric,
computes derived metrics (margins + TTM aggregates), and returns a
structured FundamentalReport.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.model.database import FundamentalDataRow
from app.modules.fundamental.schema import (
    FundamentalReport,
    MetricCategory,
    MetricPercentile,
    PeriodValues,
    QuarterlySeries,
    QuarterPoint,
)

# ── What we show on the percentile dashboard ────────────────────────
DISPLAY_METRICS: list[tuple[str, str, MetricCategory]] = [
    ("pbv", "PBV", "valuation"),
    ("per", "PER", "valuation"),
    ("ps", "PS", "valuation"),
    ("book_value_per_share", "Book Value/Share", "valuation"),
    ("roe", "ROE", "quality"),
    ("roa", "ROA", "quality"),
    ("npm", "NPM", "quality"),
    ("opm", "OPM", "quality"),
    ("gpm", "GPM", "quality"),
    ("ebitda", "EBITDA", "growth"),
    ("revenue", "Revenue", "growth"),
    ("net_income", "Net Income", "growth"),
    ("eps", "EPS", "growth"),
    ("revenue_ttm", "Revenue TTM", "ttm"),
    ("net_income_ttm", "Net Income TTM", "ttm"),
    ("eps_ttm", "EPS TTM", "ttm"),
]

QUARTERLY_DISPLAY: list[tuple[str, str]] = [
    ("opm", "OPM"),
    ("npm", "NPM"),
    ("roa", "ROA"),
    ("roe", "ROE"),
]
QUARTERLY_LOOKBACK = 12

TIME_SERIES_COLUMNS: list[tuple[str, str]] = [
    ("pbv", "PBV"),
    ("der", "DER"),
    ("per", "PER"),
    ("eps", "EPS"),
    ("eps_ttm", "EPS TTM"),
    ("sps", "SPS"),
    ("sps_ttm", "SPS TTM"),
    ("ps", "P/S"),
]
TIME_SERIES_LOOKBACK = 10

COMPARISON_METRICS = ("price", "eps", "revenue", "per")
COMPARISON_LOOKBACK = 24


async def get_fundamental_report(
    symbol: str, session: AsyncSession
) -> FundamentalReport:
    symbol = symbol.upper()

    db_rows = (
        await session.exec(
            select(FundamentalDataRow).where(FundamentalDataRow.symbol == symbol)
        )
    ).all()

    if not db_rows:
        return _empty(symbol, "no data rows in the database")

    series = _group_by_metric(db_rows)
    series = _add_derived_metrics(series)

    latest = _latest_period(series)
    if latest is None:
        return _empty(symbol, "no dated rows in the database")

    metrics = _build_percentile_rows(series, latest)
    quarterly = _build_quarterly_series(series)
    time_series = _build_time_series(series)
    comparison = _build_comparison_series(series)
    reading = _placeholder_reading(symbol, metrics)

    return FundamentalReport(
        symbol=symbol,
        name=symbol,
        as_of=latest,
        metrics=metrics,
        quarterly=quarterly,
        time_series=time_series,
        comparison=comparison,
        reading=reading,
    )


# ── Internals ────────────────────────────────────────────────────────


def _group_by_metric(rows: list[FundamentalDataRow]) -> dict[str, dict[date, float]]:
    grouped: dict[str, dict[date, float]] = defaultdict(dict)
    for row in rows:
        if row.metric == "shares_outstanding_ratio_view":
            continue
        grouped[row.metric][row.period_end] = row.value
    return grouped


def _latest_period(series: dict[str, dict[date, float]]) -> date | None:
    periods: set[date] = set()
    for values in series.values():
        periods.update(values.keys())
    return max(periods) if periods else None


def _add_derived_metrics(
    series: dict[str, dict[date, float]],
) -> dict[str, dict[date, float]]:
    revenue = series.get("revenue", {})
    net_income = series.get("net_income", {})
    operating_profit = series.get("operating_profit", {})
    gross_profit = series.get("gross_profit", {})
    eps = series.get("eps", {})
    total_liabilities = series.get("total_liabilities", {})
    total_equity = series.get("total_equity", {})
    shares = series.get("shares_outstanding", {})

    series["npm"] = _ratio(net_income, revenue)
    series["opm"] = _ratio(operating_profit, revenue)
    series["gpm"] = _ratio(gross_profit, revenue)
    series["der"] = _plain_ratio(total_liabilities, total_equity)
    series["sps"] = _plain_ratio(revenue, shares)

    series["revenue_ttm"] = _ttm(revenue)
    series["net_income_ttm"] = _ttm(net_income)
    series["eps_ttm"] = _ttm(eps)
    series["sps_ttm"] = _plain_ratio(series["revenue_ttm"], shares)
    series["price"] = _multiply(series.get("per", {}), eps)

    return series


def _multiply(a: dict[date, float], b: dict[date, float]) -> dict[date, float]:
    return {p: av * b[p] for p, av in a.items() if p in b}


def _ratio(num: dict[date, float], den: dict[date, float]) -> dict[date, float]:
    return {p: (v / den[p]) * 100 for p, v in num.items() if den.get(p)}


def _plain_ratio(num: dict[date, float], den: dict[date, float]) -> dict[date, float]:
    return {p: v / den[p] for p, v in num.items() if den.get(p)}


def _ttm(quarterly: dict[date, float]) -> dict[date, float]:
    sorted_periods = sorted(quarterly.keys())
    out: dict[date, float] = {}
    for i, period in enumerate(sorted_periods):
        if i < 3:
            continue
        window = sorted_periods[i - 3 : i + 1]
        out[period] = sum(quarterly[p] for p in window)
    return out


def _build_percentile_rows(
    series: dict[str, dict[date, float]], latest: date
) -> list[MetricPercentile]:
    rows: list[MetricPercentile] = []
    for key, display, category in DISPLAY_METRICS:
        values = series.get(key)
        if not values or latest not in values:
            continue
        current = values[latest]
        history = list(values.values())
        rows.append(
            MetricPercentile(
                metric=display,
                category=category,
                current=round(current, 4),
                percentile=round(_percentile_rank(history, current), 2),
                min_value=round(min(history), 4),
                max_value=round(max(history), 4),
            )
        )
    return rows


def _percentile_rank(values: list[float], current: float) -> float:
    if len(values) < 2:
        return 50.0
    return sum(1 for v in values if v < current) / len(values) * 100


def _build_quarterly_series(
    series: dict[str, dict[date, float]],
) -> list[QuarterlySeries]:
    out: list[QuarterlySeries] = []
    for key, display in QUARTERLY_DISPLAY:
        values = series.get(key)
        if not values:
            continue
        recent = sorted(values.items())[-QUARTERLY_LOOKBACK:]
        out.append(
            QuarterlySeries(
                metric=display,
                points=[
                    QuarterPoint(period_end=p, value=round(v, 4)) for p, v in recent
                ],
            )
        )
    return out


def _build_comparison_series(
    series: dict[str, dict[date, float]],
) -> list[PeriodValues]:
    periods: set[date] = set()
    for key in COMPARISON_METRICS:
        periods.update(series.get(key, {}).keys())
    recent = sorted(periods)[-COMPARISON_LOOKBACK:]
    return [
        PeriodValues(
            period_end=p,
            values={
                key: (
                    round(series[key][p], 4)
                    if key in series and p in series[key]
                    else None
                )
                for key in COMPARISON_METRICS
            },
        )
        for p in recent
    ]


def _build_time_series(series: dict[str, dict[date, float]]) -> list[PeriodValues]:
    tracked_keys = [key for key, _ in TIME_SERIES_COLUMNS]
    periods: set[date] = set()
    for key in tracked_keys:
        periods.update(series.get(key, {}).keys())
    recent_periods = sorted(periods)[-TIME_SERIES_LOOKBACK:]
    return [
        PeriodValues(
            period_end=period,
            values={
                key: (
                    round(series[key][period], 4)
                    if series.get(key, {}).get(period) is not None
                    else None
                )
                for key, _ in TIME_SERIES_COLUMNS
            },
        )
        for period in recent_periods
    ]


def _placeholder_reading(symbol: str, metrics: list[MetricPercentile]) -> str:
    by_name = {m.metric: m for m in metrics}
    pbv = by_name.get("PBV")
    per = by_name.get("PER")
    roe = by_name.get("ROE")
    parts = [f"{symbol} snapshot:"]
    if pbv:
        parts.append(f"PBV {pbv.current:.2f} ({pbv.percentile:.0f}th %ile of 10y).")
    if per:
        parts.append(f"PER {per.current:.2f} ({per.percentile:.0f}th %ile).")
    if roe:
        parts.append(f"ROE {roe.current:.2f}% ({roe.percentile:.0f}th %ile).")
    parts.append("Reading will be replaced by Research-agent output.")
    return " ".join(parts)


def _not_seeded(symbol: str) -> FundamentalReport:
    return FundamentalReport(
        symbol=symbol,
        name=symbol,
        as_of=date.today(),
        metrics=[],
        quarterly=[],
        time_series=[],
        comparison=[],
        reading=f"{symbol} is not in the database. Seed it via /seed first.",
    )


def _empty(symbol: str, reason: str) -> FundamentalReport:
    return FundamentalReport(
        symbol=symbol,
        name=symbol,
        as_of=date.today(),
        metrics=[],
        quarterly=[],
        time_series=[],
        comparison=[],
        reading=f"No fundamental data for {symbol}: {reason}.",
    )
