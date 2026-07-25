"""Portfolio function tools — closures bound to the current user's id."""

from __future__ import annotations

from agents import function_tool

from app.model.engine import get_session
from app.modules.ohlcv.service import fetch_candles
from app.modules.portfolio import service
from app.modules.portfolio.schema import PortfolioPositionCreate, PortfolioPositionPatch


async def _list_portfolio_impl(user_id: str) -> list[dict]:
    async for session in get_session():
        rows = await service.list_positions(session, user_id)
        return [r.model_dump(mode="json") for r in rows]
    return []  # pragma: no cover — get_session always yields once


async def _position_pnl_impl(user_id: str, ticker: str) -> dict:
    ticker = ticker.upper()
    async for session in get_session():
        rows = await service.list_positions(session, user_id)
        break
    position = next((r for r in rows if r.ticker == ticker), None)
    if position is None:
        return {"ticker": ticker, "found": False}

    candles = await fetch_candles(ticker, days=5)
    if not candles:
        return {
            "ticker": ticker,
            "found": True,
            "last_price": None,
            "note": "no price data",
        }
    last_price = candles[-1].close
    pnl_pct = ((last_price - position.avg_price) / position.avg_price) * 100
    return {
        "ticker": ticker,
        "found": True,
        "lots": position.lots,
        "avg_price": position.avg_price,
        "last_price": last_price,
        "pnl_pct": round(pnl_pct, 2),
    }


def make_portfolio_tools(user_id: str):
    """Return all portfolio function tools bound to `user_id`."""

    @function_tool(
        description_override=(
            "Return the user's full portfolio positions (ticker, lots, avg price). "
            "Call this whenever the user asks about their holdings or 'how am I doing'."
        )
    )
    async def get_portfolio() -> list[dict]:
        return await _list_portfolio_impl(user_id)

    @function_tool(
        description_override=(
            "Return current P&L for one position. Call when the user asks about a specific ticker they hold."
        )
    )
    async def get_position_pnl(ticker: str) -> dict:
        return await _position_pnl_impl(user_id, ticker)

    @function_tool(
        description_override=(
            "Add a new position to the portfolio. "
            "Use when the user says they bought a stock or wants to add a holding. "
            "ticker: IDX ticker (e.g. BBRI), lots: number of lots, avg_price: average buy price per share."
        )
    )
    async def add_position(ticker: str, lots: int, avg_price: float) -> dict:
        async for session in get_session():
            try:
                pos = await service.add_position(
                    session,
                    user_id,
                    PortfolioPositionCreate(
                        ticker=ticker.upper(), lots=lots, avg_price=avg_price
                    ),
                )
                return {
                    "ok": True,
                    "ticker": pos.ticker,
                    "lots": pos.lots,
                    "avg_price": pos.avg_price,
                }
            except ValueError as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "no session"}

    @function_tool(
        description_override=(
            "Update an existing position's lots or average price. "
            "Use when the user says they added more shares (average down/up) or corrects a value. "
            "Pass only the fields that should change."
        )
    )
    async def update_position(
        ticker: str, lots: int | None = None, avg_price: float | None = None
    ) -> dict:
        async for session in get_session():
            try:
                pos = await service.update_position(
                    session,
                    user_id,
                    ticker.upper(),
                    PortfolioPositionPatch(lots=lots, avg_price=avg_price),
                )
                return {
                    "ok": True,
                    "ticker": pos.ticker,
                    "lots": pos.lots,
                    "avg_price": pos.avg_price,
                }
            except LookupError as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "no session"}

    @function_tool(
        description_override=(
            "Remove a position from the portfolio entirely. "
            "Use when the user says they sold all their shares of a ticker."
        )
    )
    async def delete_position(ticker: str) -> dict:
        async for session in get_session():
            await service.delete_position(session, user_id, ticker.upper())
            return {"ok": True, "ticker": ticker.upper()}
        return {"ok": False, "error": "no session"}

    return (
        get_portfolio,
        get_position_pnl,
        add_position,
        update_position,
        delete_position,
    )
