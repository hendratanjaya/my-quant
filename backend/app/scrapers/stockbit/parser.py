"""Parse Stockbit financial HTML into typed fundamental rows.

The Stockbit `/findata-view/company/financial` endpoint returns JSON like:

    { "data": { "html_report": "<div ...>" } }

`html_report` contains 2–4 HTML tables whose header row is 73 quarter labels
(`Q1 2008 ... Q1 2026`) and whose body rows are `(label, value_per_period...)`.

This module walks that HTML and yields normalized rows.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date
from typing import NamedTuple

from bs4 import BeautifulSoup

# ── Canonical metric mapping ─────────────────────────────────────────
# Maps Stockbit's raw row label → canonical metric name we persist.
# Any label not in this map is silently skipped. Add a new metric =
# add one line here.
LABEL_MAP: dict[str, str] = {
    # ── Income Statement (report_type=1, table 0) ──
    "Total Pendapatan": "revenue",
    "Laba Kotor": "gross_profit",
    "Laba Usaha": "operating_profit",
    "Laba Bersih Tahun Berjalan": "net_income",
    # ── Profitability ratios (report_type=1, table 1) ──
    "Share Outstanding": "shares_outstanding_ratio_view",
    "EPS (Quarter)": "eps",
    "PE Ratio (Quarter)": "per",
    "Price to Sales (Quarter)": "ps",
    "EBITDA (Quarter)": "ebitda",
    "Return on Assets (Quarter)": "roa",
    "Return on Equity (Quarter)": "roe",
    # ── Balance Sheet (report_type=2, table 0) ──
    "TotalAset": "total_assets",
    "TotalLiabilitas": "total_liabilities",
    "TotalEkuitas": "total_equity",
    "Saham Beredar": "shares_outstanding",
    # ── BS ratios (report_type=2, table 1) ──
    "Price to Book Value (Quarter)": "pbv",
    "Book Value Per Share (Quarter)": "book_value_per_share",
}

_QUARTER_END_DAY = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}


class FundamentalRow(NamedTuple):
    """A single (symbol, period, metric, value) tuple ready for insert."""

    symbol: str
    period_end: date
    metric: str
    value: float


def parse_html_report(symbol: str, html: str) -> Iterator[FundamentalRow]:
    """Yield fundamental rows from a Stockbit `html_report` string.

    Walks every table, every row. Skips rows whose label isn't in LABEL_MAP
    and cells whose value is missing/dash/na.
    """
    symbol = symbol.upper()
    soup = BeautifulSoup(html, "html.parser")

    periods = _extract_periods(soup)
    if not periods:
        return

    for table in soup.find_all("table"):
        tbody = table.find("tbody")
        if not tbody:
            continue
        for tr in tbody.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            label = _clean_label(cells[0].get_text(strip=True))
            metric = LABEL_MAP.get(label)
            if not metric:
                continue
            for i, cell in enumerate(cells[1 : 1 + len(periods)]):
                value = _parse_value(cell.get_text(strip=True))
                if value is None:
                    continue
                yield FundamentalRow(
                    symbol=symbol,
                    period_end=periods[i],
                    metric=metric,
                    value=value,
                )


# ── Internals ────────────────────────────────────────────────────────


def _extract_periods(soup: BeautifulSoup) -> list[date]:
    """Read the first table's `<thead>` to get one date per column."""
    table = soup.find("table")
    if not table:
        return []
    thead = table.find("thead")
    if not thead:
        return []
    cells = thead.find_all(["th", "td"])
    # First cell is a units label ("In Million"). The rest are quarter labels.
    return [_parse_quarter(c.get_text(strip=True)) for c in cells[1:]]


def _parse_quarter(label: str) -> date:
    """'Q1 2008' → date(2008, 3, 31)."""
    q, y = label.strip().split()
    month, day = _QUARTER_END_DAY[q]
    return date(int(y), month, day)


def _clean_label(raw: str) -> str:
    """Normalize a label cell: strip HTML entities and whitespace."""
    return raw.replace("\xa0", " ").replace("&nbsp", "").strip()


_NUMBER_RE = re.compile(r"^-?[\d,]+(?:\.\d+)?$")


def _parse_value(raw: str) -> float | None:
    """Turn a cell string into a float, or None if missing.

    Handles:
      - raw:            '539934000000.000000'  → 5.39934e11
      - billion suffix: '5,062 B'              → 5.062e12
      - million suffix: '3.2 M'                → 3.2e6
      - percent:        '1.59%'                → 1.59  (keep as percent value)
      - parens neg:     '(1,707 B)'            → -1.707e12
      - missing:        '', '-', 'n/a'         → None
    """
    if not raw or raw in {"-", "n/a"}:
        return None
    s = raw.strip()

    negative = False
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
        negative = True

    multiplier = 1.0
    if s.endswith(" B"):
        multiplier = 1e9
        s = s[:-2].strip()
    elif s.endswith(" M"):
        multiplier = 1e6
        s = s[:-2].strip()
    elif s.endswith("%"):
        s = s[:-1].strip()

    s = s.replace(",", "")
    if not _NUMBER_RE.match(s):
        return None

    try:
        value = float(s) * multiplier
    except ValueError:
        return None

    return -value if negative else value
