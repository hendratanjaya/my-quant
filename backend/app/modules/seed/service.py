"""Orchestrates: fetch Stockbit → parse HTML → append to JSON archive."""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.seed import storage
from app.modules.seed.schema import (
    FundamentalRowStored,
    SeededSummary,
    SeededTicker,
)
from app.scrapers.stockbit import fetcher
from app.scrapers.stockbit.parser import parse_html_report

# Which Stockbit report types we pull per ticker. 1 = Income Statement + ratios,
# 2 = Balance Sheet + ratios. Cash Flow (3) is deferred.
REPORT_TYPES = (1, 2)


class AlreadySeededError(Exception):
    """Raised when the caller tries to add a ticker that's already in the archive."""


def list_summaries() -> list[SeededSummary]:
    return [_summarize(t) for t in storage.load().values()]


async def seed_ticker(symbol: str, jwt: str) -> SeededSummary:
    symbol = symbol.upper()
    store = storage.load()
    if symbol in store:
        raise AlreadySeededError(f"{symbol} already seeded")

    all_rows: list[FundamentalRowStored] = []
    for report_type in REPORT_TYPES:
        payload = await fetcher.fetch_financial(symbol, jwt, report_type=report_type)
        html = payload["data"]["html_report"]
        for row in parse_html_report(symbol, html):
            all_rows.append(
                FundamentalRowStored(
                    period_end=row.period_end,
                    metric=row.metric,
                    value=row.value,
                )
            )

    ticker = SeededTicker(
        symbol=symbol,
        seeded_at=datetime.now(UTC),
        rows=all_rows,
    )
    store[symbol] = ticker
    storage.save(store)
    return _summarize(ticker)


def _summarize(ticker: SeededTicker) -> SeededSummary:
    periods = [r.period_end for r in ticker.rows]
    return SeededSummary(
        symbol=ticker.symbol,
        seeded_at=ticker.seeded_at,
        row_count=len(ticker.rows),
        period_first=min(periods) if periods else None,
        period_last=max(periods) if periods else None,
    )
