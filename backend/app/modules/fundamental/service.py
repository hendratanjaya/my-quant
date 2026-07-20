"""Build a fundamental report from the seeded Stockbit archive.

Reads `backend/data/seeded.json` via the seed module's storage, groups rows by
metric, computes derived metrics (margins + TTM aggregates), and returns a
structured `FundamentalReport`. The FE renders this as percentile bars +
quarterly charts.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.modules.fundamental.schema import (
    FundamentalReport,
    MetricCategory,
    MetricPercentile,
    PeriodValues,
    QuarterlySeries,
    QuarterPoint,
)
from app.modules.seed import storage

# ── What we show on the percentile dashboard ────────────────────────
# Ordered — this is the display order in the FE.
# Each entry: (raw metric key, display name, category)
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

# Metrics shown as quarterly bar charts.
QUARTERLY_DISPLAY: list[tuple[str, str]] = [
    ("opm", "OPM"),
    ("npm", "NPM"),
    ("roa", "ROA"),
    ("roe", "ROE"),
]
QUARTERLY_LOOKBACK = 12

# Columns shown in the tabular time-series view (in display order).
# Each entry: (metric key, display label)
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

# Metrics on the "Price & EPS historical" overlay chart. All min-max normalized on
# the FE so they overlay cleanly on a single [0, 100] axis.
COMPARISON_METRICS = ("price", "eps", "revenue", "per")
COMPARISON_LOOKBACK = 24


def get_fundamental_report(symbol: str) -> FundamentalReport:
    symbol = symbol.upper()
    store = storage.load()
    if symbol not in store:
        return _not_seeded(symbol)

    ticker = store[symbol]
    series = _group_by_metric(ticker)
    series = _add_derived_metrics(series)

    latest = _latest_period(series)
    if latest is None:
        return _empty(symbol, "no dated rows in the archive")

    metrics = _build_percentile_rows(series, latest)
    quarterly = _build_quarterly_series(series, latest)
    time_series = _build_time_series(series, latest)
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


def _group_by_metric(ticker) -> dict[str, dict[date, float]]:
    grouped: dict[str, dict[date, float]] = defaultdict(dict)
    for row in ticker.rows:
        # Skip the ratio-tab shares outstanding when the balance-sheet one is present.
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
    """Compute margins, per-share, leverage, and TTM aggregates from raw quarterly values."""
    revenue = series.get("revenue", {})
    net_income = series.get("net_income", {})
    operating_profit = series.get("operating_profit", {})
    gross_profit = series.get("gross_profit", {})
    eps = series.get("eps", {})
    total_liabilities = series.get("total_liabilities", {})
    total_equity = series.get("total_equity", {})
    shares = series.get("shares_outstanding", {})

    # Margins (as percent) — divide by revenue on matching periods.
    series["npm"] = _ratio(net_income, revenue)
    series["opm"] = _ratio(operating_profit, revenue)
    series["gpm"] = _ratio(gross_profit, revenue)

    # Debt to Equity (a ratio, not a percent) — divide as-is.
    series["der"] = _plain_ratio(total_liabilities, total_equity)

    # Sales Per Share.
    series["sps"] = _plain_ratio(revenue, shares)

    # TTM = sum of the current quarter plus the previous three.
    series["revenue_ttm"] = _ttm(revenue)
    series["net_income_ttm"] = _ttm(net_income)
    series["eps_ttm"] = _ttm(eps)
    series["sps_ttm"] = _plain_ratio(series["revenue_ttm"], shares)

    # Implicit historical price per quarter: Stockbit's quarterly `per` is
    # price / eps_qtr, so price = per × eps_qtr. Lets us plot Price alongside
    # EPS/Revenue/PER without a separate OHLCV round-trip per ticker.
    per = series.get("per", {})
    series["price"] = _multiply(per, eps)

    return series


def _multiply(
    a: dict[date, float],
    b: dict[date, float],
) -> dict[date, float]:
    out: dict[date, float] = {}
    for period, av in a.items():
        bv = b.get(period)
        if bv is None:
            continue
        out[period] = av * bv
    return out


def _ratio(numerator: dict[date, float], denominator: dict[date, float]) -> dict[date, float]:
    out: dict[date, float] = {}
    for period, num in numerator.items():
        denom = denominator.get(period)
        if denom is None or denom == 0:
            continue
        out[period] = (num / denom) * 100  # store as percent
    return out


def _plain_ratio(
    numerator: dict[date, float],
    denominator: dict[date, float],
) -> dict[date, float]:
    """Like `_ratio` but without the ×100 percent conversion — for DER, SPS, etc."""
    out: dict[date, float] = {}
    for period, num in numerator.items():
        denom = denominator.get(period)
        if denom is None or denom == 0:
            continue
        out[period] = num / denom
    return out


def _ttm(quarterly: dict[date, float]) -> dict[date, float]:
    """For each period, sum this quarter + the three preceding it (if present)."""
    sorted_periods = sorted(quarterly.keys())
    period_to_idx = {p: i for i, p in enumerate(sorted_periods)}
    out: dict[date, float] = {}
    for period, idx in period_to_idx.items():
        if idx < 3:
            continue
        window = sorted_periods[idx - 3 : idx + 1]
        out[period] = sum(quarterly[p] for p in window)
    return out


def _build_percentile_rows(
    series: dict[str, dict[date, float]],
    latest: date,
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
    below = sum(1 for v in values if v < current)
    return (below / len(values)) * 100


def _build_quarterly_series(
    series: dict[str, dict[date, float]],
    latest: date,
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
    """Wider-history block for the overlay chart. Fewer metrics, more periods."""
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


def _build_time_series(
    series: dict[str, dict[date, float]],
    latest: date,
) -> list[PeriodValues]:
    """Assemble a per-quarter row containing every column in TIME_SERIES_COLUMNS."""
    # Collect all periods that have any of the target columns present.
    tracked_keys = [key for key, _ in TIME_SERIES_COLUMNS]
    periods: set[date] = set()
    for key in tracked_keys:
        periods.update(series.get(key, {}).keys())
    recent_periods = sorted(periods)[-TIME_SERIES_LOOKBACK:]

    rows: list[PeriodValues] = []
    for period in recent_periods:
        row: dict[str, float | None] = {}
        for key, _ in TIME_SERIES_COLUMNS:
            v = series.get(key, {}).get(period)
            row[key] = round(v, 4) if v is not None else None
        rows.append(PeriodValues(period_end=period, values=row))
    return rows


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
        reading=f"{symbol} is not in the archive. Seed it via /seed first.",
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
