from datetime import datetime as DateTime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.model.database import PortfolioPosition
from app.modules.portfolio.schema import (
    PortfolioPositionCreate,
    PortfolioPositionPatch,
    PortfolioPositionRead,
)


def _to_read(row: PortfolioPosition) -> PortfolioPositionRead:
    return PortfolioPositionRead(
        ticker=row.ticker,
        lots=row.lots,
        avg_price=row.avg_price,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_positions(
    session: AsyncSession, user_id: str
) -> list[PortfolioPositionRead]:
    stmt = select(PortfolioPosition).where(PortfolioPosition.user_id == user_id)
    rows = (await session.exec(stmt)).all()
    return [_to_read(r) for r in rows]


async def add_position(
    session: AsyncSession, user_id: str, payload: PortfolioPositionCreate
) -> PortfolioPositionRead:
    ticker = payload.ticker.upper()
    stmt = select(PortfolioPosition).where(
        PortfolioPosition.user_id == user_id,
        PortfolioPosition.ticker == ticker,
    )
    existing = (await session.exec(stmt)).first()
    if existing is not None:
        raise ValueError(f"Position for {ticker} already exists")
    row = PortfolioPosition(
        user_id=user_id,
        ticker=ticker,
        lots=payload.lots,
        avg_price=payload.avg_price,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_read(row)


async def update_position(
    session: AsyncSession, user_id: str, ticker: str, patch: PortfolioPositionPatch
) -> PortfolioPositionRead:
    ticker = ticker.upper()
    stmt = select(PortfolioPosition).where(
        PortfolioPosition.user_id == user_id, PortfolioPosition.ticker == ticker
    )
    row = (await session.exec(stmt)).first()
    if row is None:
        raise LookupError(f"No position for {ticker}")
    if patch.lots is not None:
        row.lots = patch.lots
    if patch.avg_price is not None:
        row.avg_price = patch.avg_price
    row.updated_at = DateTime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_read(row)


async def delete_position(session: AsyncSession, user_id: str, ticker: str) -> None:
    ticker = ticker.upper()
    stmt = select(PortfolioPosition).where(
        PortfolioPosition.user_id == user_id, PortfolioPosition.ticker == ticker
    )
    row = (await session.exec(stmt)).first()
    if row is None:
        return
    await session.delete(row)
    await session.commit()
