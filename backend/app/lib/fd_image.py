"""Render a FundamentalReport as a dark-themed PNG dashboard."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from app.modules.fundamental.schema import (
    FundamentalReport,
    MetricPercentile,
    PeriodValues,
    QuarterlySeries,
)

# ── Palette ──────────────────────────────────────────────────────────────────
BG = "#0a0a0a"
FG = "#e2e8f0"
MUTED = "#64748b"
TRACK = "#1e293b"
ALT = "#0f172a"
GREEN = "#22c55e"
RED = "#ef4444"
AMBER = "#f59e0b"
BLUE = "#3b82f6"
PINK = "#ec4899"
CYAN = "#06b6d4"

# ── Layout constants (inches) ─────────────────────────────────────────────────
FIG_W = 9.0
DPI = 150
ROW_H = 0.265  # metric bar row
CAT_H = 0.28  # category label row
CHART_H = 1.75  # one quarterly mini-chart
GAP = 0.10  # inter-section spacing
TS_RH = 0.215  # time-series table data row

CAT_ORDER = ["valuation", "quality", "growth", "ttm"]
CAT_LABELS = {
    "valuation": "VALUATION",
    "quality": "PROFITABILITY",
    "growth": "GROWTH (QUARTERLY)",
    "ttm": "GROWTH (TTM)",
}

CMP_KEYS = ["price", "eps", "revenue", "per"]
CMP_COLORS = {"price": GREEN, "eps": PINK, "revenue": CYAN, "per": AMBER}
CMP_LABELS = {"price": "Price", "eps": "EPS", "revenue": "Revenue", "per": "PER"}

TS_COLS = [
    ("pbv", "PBV"),
    ("der", "DER"),
    ("per", "PER"),
    ("eps", "EPS"),
    ("eps_ttm", "EPS TTM"),
    ("sps", "SPS"),
    ("sps_ttm", "SPS TTM"),
    ("ps", "P/S"),
]


# ── Number formatting ─────────────────────────────────────────────────────────


def _fmt(v: float | None) -> str:
    """Human-readable number: 2.1e+13 → 21.0T, 1500000 → 1.50M, 1.23 → 1.23."""
    if v is None:
        return "—"
    abs_v = abs(v)
    if abs_v >= 1e12:
        return f"{v / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{v / 1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{v / 1e3:.2f}K"
    return f"{v:.3g}"


# ── Public entry point ────────────────────────────────────────────────────────


def render_fd_image(report: FundamentalReport) -> bytes:
    if not report.metrics:
        return _error_image(f"{report.symbol}\n{report.reading}")

    by_cat: dict[str, list[MetricPercentile]] = {c: [] for c in CAT_ORDER}
    for m in report.metrics:
        by_cat[m.category].append(m)

    # ── Calculate total figure height ─────────────────────────────────────────
    header_h = 0.60

    bars_h = sum(CAT_H + len(rows) * ROW_H for rows in by_cat.values() if rows) + GAP

    q_h = (0.28 + 2 * CHART_H + 0.12 + GAP) if report.quarterly else 0

    cmp_h = (0.42 + 2.6 + GAP) if report.comparison else 0

    n_ts = len(report.time_series)
    ts_h = (0.28 + 0.26 + n_ts * TS_RH + GAP) if report.time_series else 0

    reading_h = 0.55

    fig_h = header_h + bars_h + q_h + cmp_h + ts_h + reading_h + 0.15

    fig = Figure(figsize=(FIG_W, fig_h), facecolor=BG)

    def ax(x_in, y_top_in, w_in, h_in):
        """Add axes using top-left inch coordinates."""
        rect = [
            x_in / FIG_W,
            (fig_h - y_top_in - h_in) / fig_h,
            w_in / FIG_W,
            h_in / fig_h,
        ]
        a = fig.add_axes(rect)
        a.set_facecolor(BG)
        a.axis("off")
        return a

    # ── Header ────────────────────────────────────────────────────────────────
    y = 0.0
    a = ax(0, y, FIG_W, header_h)
    a.text(
        0.015,
        0.60,
        report.symbol,
        transform=a.transAxes,
        color=FG,
        fontsize=17,
        fontweight="bold",
        va="center",
    )
    a.text(
        0.985,
        0.60,
        f"as of {report.as_of}",
        transform=a.transAxes,
        color=MUTED,
        fontsize=8.5,
        va="center",
        ha="right",
    )
    y += header_h

    # ── Percentile bars ───────────────────────────────────────────────────────
    for cat in CAT_ORDER:
        rows = by_cat[cat]
        if not rows:
            continue
        a = ax(0, y, FIG_W, CAT_H)
        a.text(
            0.015,
            0.45,
            CAT_LABELS[cat],
            transform=a.transAxes,
            color=MUTED,
            fontsize=7,
            fontweight="bold",
            va="center",
        )
        y += CAT_H

        for m in rows:
            a = ax(0, y, FIG_W, ROW_H)
            _draw_bar_row(a, m)
            y += ROW_H
    y += GAP

    # ── Quarterly mini-charts ─────────────────────────────────────────────────
    if report.quarterly:
        a = ax(0, y, FIG_W, 0.28)
        a.text(
            0.015,
            0.45,
            "QUARTERLY (LAST 12)",
            transform=a.transAxes,
            color=MUTED,
            fontsize=7,
            fontweight="bold",
            va="center",
        )
        y += 0.28

        cw = (FIG_W - 0.10) / 2
        for i, series in enumerate(report.quarterly[:4]):
            col = i % 2
            row = i // 2
            x_pos = col * (cw + 0.10)
            y_pos = y + row * (CHART_H + 0.12)
            _draw_quarterly_chart(fig, x_pos, y_pos, cw, CHART_H, series, fig_h)

        y += 2 * CHART_H + 0.12 + GAP

    # ── Comparison line chart ─────────────────────────────────────────────────
    if report.comparison:
        # Header + legend
        a = ax(0, y, FIG_W, 0.42)
        latest = report.comparison[-1]
        a.text(
            0.015,
            0.92,
            "PRICE & EPS HISTORICAL (LAST 24 QUARTERS)",
            transform=a.transAxes,
            color=MUTED,
            fontsize=7,
            fontweight="bold",
            va="top",
        )
        lx = 0.015
        for key in CMP_KEYS:
            val = latest.values.get(key)
            val_str = _fmt(val) if val is not None else "—"
            label = f"● {CMP_LABELS[key]} {val_str}"
            a.text(
                lx,
                0.08,
                label,
                transform=a.transAxes,
                color=CMP_COLORS[key],
                fontsize=7,
                va="bottom",
            )
            lx += 0.145
        y += 0.42

        _draw_comparison_chart(
            fig, 0.10, y, FIG_W - 0.15, 2.6, report.comparison, fig_h
        )
        y += 2.6 + GAP

    # ── Time-series table ─────────────────────────────────────────────────────
    if report.time_series:
        a = ax(0, y, FIG_W, 0.28)
        a.text(
            0.015,
            0.45,
            f"VALUE VS GROWTH (LAST {n_ts} QUARTERS)",
            transform=a.transAxes,
            color=MUTED,
            fontsize=7,
            fontweight="bold",
            va="center",
        )
        y += 0.28

        table_h = 0.26 + n_ts * TS_RH
        a = ax(0, y, FIG_W, table_h)
        _draw_table(a, report.time_series, 0.26, TS_RH, table_h)
        y += table_h + GAP

    # ── Reading text ──────────────────────────────────────────────────────────
    a = ax(0, y, FIG_W, reading_h)
    a.text(
        0.015,
        0.92,
        report.reading,
        transform=a.transAxes,
        color=MUTED,
        fontsize=7.5,
        va="top",
        wrap=True,
        multialignment="left",
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=BG, edgecolor="none")
    plt.close("all")
    buf.seek(0)
    return buf.read()


# ── Section renderers ─────────────────────────────────────────────────────────


def _draw_bar_row(a, m: MetricPercentile) -> None:
    BAR_L = 0.220
    BAR_W = 0.560
    VAL_X = 0.790
    PCT_X = 0.985

    a.text(
        0.015, 0.52, m.metric, transform=a.transAxes, color=FG, fontsize=8, va="center"
    )

    # Track
    a.add_patch(
        mpatches.FancyBboxPatch(
            (BAR_L, 0.30),
            BAR_W,
            0.40,
            boxstyle="round,pad=0",
            linewidth=0,
            facecolor=TRACK,
            transform=a.transAxes,
            clip_on=False,
        )
    )
    # Fill
    fill = max(BAR_W * m.percentile / 100, 0.002)
    a.add_patch(
        mpatches.FancyBboxPatch(
            (BAR_L, 0.30),
            fill,
            0.40,
            boxstyle="round,pad=0",
            linewidth=0,
            facecolor=GREEN,
            alpha=0.85,
            transform=a.transAxes,
            clip_on=False,
        )
    )

    a.text(
        VAL_X,
        0.52,
        _fmt(m.current),
        transform=a.transAxes,
        color=FG,
        fontsize=7.5,
        va="center",
    )
    a.text(
        PCT_X,
        0.52,
        f"{m.percentile:.0f}%",
        transform=a.transAxes,
        color=MUTED,
        fontsize=7.5,
        va="center",
        ha="right",
    )


def _draw_quarterly_chart(
    fig: Figure,
    x_in: float,
    y_top_in: float,
    w_in: float,
    h_in: float,
    series: QuarterlySeries,
    fig_h: float,
) -> None:
    rect = [x_in / FIG_W, (fig_h - y_top_in - h_in) / fig_h, w_in / FIG_W, h_in / fig_h]
    ax = fig.add_axes(rect)
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_visible(False)

    pts = series.points
    if not pts:
        ax.axis("off")
        return

    vals = [p.value for p in pts]
    x = np.arange(len(vals))
    ax.bar(x, vals, color=GREEN, width=0.75, alpha=0.85)

    # Value labels under each bar
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{v:.1f}" for v in vals], fontsize=4.5, color=MUTED, rotation=0
    )

    ax.tick_params(axis="x", length=0, pad=2)
    ax.tick_params(axis="y", colors=MUTED, labelsize=5.5, length=2)
    ax.yaxis.grid(True, color=TRACK, linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)

    mn, mx = min(vals), max(vals)
    pad = (mx - mn) * 0.25 if mx != mn else abs(mx) * 0.1 or 0.5
    ax.set_ylim(max(0, mn - pad), mx + pad * 2.2)
    ax.set_xlim(-0.6, len(x) - 0.4)

    # Metric name top-left
    ax.text(
        0.02,
        0.97,
        series.metric,
        transform=ax.transAxes,
        color=MUTED,
        fontsize=8.5,
        fontweight="bold",
        va="top",
    )
    # Latest value top-right
    ax.text(
        0.98,
        0.97,
        f"{vals[-1]:.1f}%",
        transform=ax.transAxes,
        color=RED,
        fontsize=8.5,
        fontweight="bold",
        va="top",
        ha="right",
    )


def _draw_comparison_chart(
    fig: Figure,
    x_in: float,
    y_top_in: float,
    w_in: float,
    h_in: float,
    comparison: list[PeriodValues],
    fig_h: float,
) -> None:
    rect = [x_in / FIG_W, (fig_h - y_top_in - h_in) / fig_h, w_in / FIG_W, h_in / fig_h]
    ax = fig.add_axes(rect)
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_edgecolor(TRACK)
        spine.set_linewidth(0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    n = len(comparison)
    for key in CMP_KEYS:
        raw = [p.values.get(key) for p in comparison]
        valid = [v for v in raw if v is not None]
        if not valid:
            continue
        mn, mx = min(valid), max(valid)
        span = mx - mn if mx != mn else 1.0
        normed = [(v - mn) / span * 100 if v is not None else np.nan for v in raw]
        ax.plot(normed, color=CMP_COLORS[key], linewidth=1.1, alpha=0.9)

    # Year x-ticks
    year_ticks, year_labels = [], []
    seen: set[str] = set()
    for i, p in enumerate(comparison):
        yr = str(p.period_end)[:4]
        if yr not in seen:
            year_ticks.append(i)
            year_labels.append(yr)
            seen.add(yr)

    ax.set_xticks(year_ticks)
    ax.set_xticklabels(year_labels, fontsize=7, color=MUTED)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(-5, 108)
    ax.tick_params(axis="x", colors=MUTED, length=3)
    ax.tick_params(axis="y", colors=MUTED, labelsize=6, length=2)
    ax.yaxis.grid(True, color=TRACK, linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)


def _draw_table(
    a,
    time_series: list[PeriodValues],
    header_h_frac_abs: float,
    row_h_abs: float,
    total_h_abs: float,
) -> None:
    """Draw the time-series table on a pre-created (axis-off) axes."""
    n_rows = len(time_series)
    total_rows = n_rows + 1  # +1 header
    row_frac = 1.0 / total_rows

    PERIOD_W = 0.125
    n_cols = len(TS_COLS)
    col_w = (1.0 - PERIOD_W) / n_cols

    def col_x(j: int) -> float:
        return PERIOD_W + (j + 0.5) * col_w

    # Header
    hy = 1 - 0.5 * row_frac
    a.text(
        0.015,
        hy,
        "Period",
        transform=a.transAxes,
        color=MUTED,
        fontsize=6.5,
        va="center",
        fontweight="bold",
    )
    for j, (_, label) in enumerate(TS_COLS):
        a.text(
            col_x(j),
            hy,
            label,
            transform=a.transAxes,
            color=MUTED,
            fontsize=6.5,
            va="center",
            ha="center",
            fontweight="bold",
        )

    # Data rows (newest first)
    for i, pv in enumerate(reversed(time_series)):
        ry = 1 - (i + 1.5) * row_frac
        # Alternate row
        if i % 2 == 0:
            a.add_patch(
                mpatches.Rectangle(
                    (0, 1 - (i + 2) * row_frac),
                    1,
                    row_frac,
                    transform=a.transAxes,
                    facecolor=ALT,
                    linewidth=0,
                    zorder=0,
                )
            )
        a.text(
            0.015,
            ry,
            str(pv.period_end),
            transform=a.transAxes,
            color=FG,
            fontsize=6.5,
            va="center",
        )
        for j, (key, _) in enumerate(TS_COLS):
            val = pv.values.get(key)
            s = _fmt(val) if val is not None else "—"
            a.text(
                col_x(j),
                ry,
                s,
                transform=a.transAxes,
                color=FG,
                fontsize=6.5,
                va="center",
                ha="center",
            )


# ── Error fallback ────────────────────────────────────────────────────────────


def _error_image(text: str) -> bytes:
    fig = Figure(figsize=(6, 1.5), facecolor=BG)
    a = fig.add_axes([0, 0, 1, 1])
    a.set_facecolor(BG)
    a.axis("off")
    a.text(
        0.5,
        0.5,
        text,
        color=FG,
        fontsize=10,
        ha="center",
        va="center",
        transform=a.transAxes,
    )
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, facecolor=BG)
    plt.close("all")
    buf.seek(0)
    return buf.read()
