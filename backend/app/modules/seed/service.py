"""Orchestrates: fetch Stockbit → parse HTML → persist to database."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.model.database import FundamentalDataRow
from app.modules.seed.schema import PaginatedSeededSummary, SeededSummary
from app.scrapers.stockbit import fetcher
from app.scrapers.stockbit.parser import parse_html_report

REPORT_TYPES = (1, 2)


class AlreadySeededError(Exception):
    pass


async def list_summaries(session: AsyncSession) -> list[SeededSummary]:
    rows = (await session.exec(select(FundamentalDataRow))).all()
    by_symbol: dict[str, list[FundamentalDataRow]] = {}
    for row in rows:
        by_symbol.setdefault(row.symbol, []).append(row)
    return [
        SeededSummary(
            symbol=symbol,
            seeded_at=datetime.now(UTC),
            row_count=len(rs),
            period_first=min(r.period_end for r in rs),
            period_last=max(r.period_end for r in rs),
        )
        for symbol, rs in sorted(by_symbol.items())
    ]


async def list_summaries_paginated(
    session: AsyncSession, page: int = 1, page_size: int = 20
) -> PaginatedSeededSummary:
    total_result = await session.execute(
        select(func.count(FundamentalDataRow.symbol.distinct()))
    )
    total = total_result.scalar_one()

    stmt = (
        select(
            FundamentalDataRow.symbol,
            func.count(FundamentalDataRow.id).label("row_count"),
            func.min(FundamentalDataRow.period_end).label("period_first"),
            func.max(FundamentalDataRow.period_end).label("period_last"),
        )
        .group_by(FundamentalDataRow.symbol)
        .order_by(FundamentalDataRow.symbol)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    items = [
        SeededSummary(
            symbol=row.symbol,
            seeded_at=datetime.now(UTC),
            row_count=row.row_count,
            period_first=row.period_first,
            period_last=row.period_last,
        )
        for row in result.all()
    ]

    return PaginatedSeededSummary(items=items, total=total, page=page, page_size=page_size)


async def upsert_ticker(symbol: str, jwt: str, session: AsyncSession) -> SeededSummary:
    symbol = symbol.upper()
    await session.exec(delete(FundamentalDataRow).where(FundamentalDataRow.symbol == symbol))

    all_rows: list[FundamentalDataRow] = []
    for report_type in REPORT_TYPES:
        payload = await fetcher.fetch_financial(symbol, jwt, report_type=report_type)
        html = payload["data"]["html_report"]
        for row in parse_html_report(symbol, html):
            all_rows.append(
                FundamentalDataRow(
                    symbol=symbol,
                    period_end=row.period_end,
                    metric=row.metric,
                    value=row.value,
                )
            )

    for row in all_rows:
        session.add(row)
    await session.commit()

    periods = [r.period_end for r in all_rows]
    return SeededSummary(
        symbol=symbol,
        seeded_at=datetime.now(UTC),
        row_count=len(all_rows),
        period_first=min(periods) if periods else None,
        period_last=max(periods) if periods else None,
    )


async def seed_ticker(symbol: str, jwt: str, session: AsyncSession) -> SeededSummary:
    symbol = symbol.upper()

    existing = (
        await session.exec(
            select(FundamentalDataRow)
            .where(FundamentalDataRow.symbol == symbol)
            .limit(1)
        )
    ).first()
    if existing:
        raise AlreadySeededError(f"{symbol} already seeded")

    all_rows: list[FundamentalDataRow] = []
    for report_type in REPORT_TYPES:
        payload = await fetcher.fetch_financial(symbol, jwt, report_type=report_type)
        html = payload["data"]["html_report"]
        for row in parse_html_report(symbol, html):
            all_rows.append(
                FundamentalDataRow(
                    symbol=symbol,
                    period_end=row.period_end,
                    metric=row.metric,
                    value=row.value,
                )
            )

    for row in all_rows:
        session.add(row)
    await session.commit()

    periods = [r.period_end for r in all_rows]
    return SeededSummary(
        symbol=symbol,
        seeded_at=datetime.now(UTC),
        row_count=len(all_rows),
        period_first=min(periods) if periods else None,
        period_last=max(periods) if periods else None,
    )
