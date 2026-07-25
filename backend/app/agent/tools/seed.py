"""list_seeded function tool — returns tickers that have fundamentals in the database."""

from __future__ import annotations

from agents import function_tool
from sqlmodel import select

from app.model.database import FundamentalDataRow
from app.model.engine import get_session


@function_tool(
    description_override=(
        "List all IDX tickers whose fundamentals are seeded in the database. "
        "Call this if the user asks about a ticker to verify it's available "
        "before attempting analysis."
    )
)
async def list_seeded() -> list[str]:
    async for session in get_session():
        result = await session.exec(select(FundamentalDataRow.symbol).distinct())
        return sorted(result.all())
    return []
