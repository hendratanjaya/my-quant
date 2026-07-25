"""Parallel data gathering tool for the Research agent.

Fetches CI signals, fundamentals, news, past readings, and portfolio position
concurrently in one asyncio.gather call — the Research agent calls this once
instead of hitting each source sequentially.
"""

from __future__ import annotations

import asyncio

from agents import function_tool

from app.agent.tools.ci import _check_ci_impl
from app.agent.tools.portfolio import _position_pnl_impl
from app.agent.tools.readings import _retrieve_impl
from app.mcp.news_server import _get_news_impl
from app.model.engine import get_session
from app.modules.fundamental.service import get_fundamental_report


def make_gather_tool(user_id: str):
    async def _fundamental_impl(ticker: str) -> dict:
        async for session in get_session():
            report = await get_fundamental_report(ticker, session)
            return report.model_dump(mode="json")
        return {}

    @function_tool(
        description_override=(
            "Gather ALL research data for an IDX ticker in one parallel call: "
            "CI (Chart Investing) framework signals, fundamental snapshot, "
            "recent Indonesian news, past agent readings, and the user's current "
            "position P&L (if any). Call this FIRST and ONLY ONCE before writing "
            "any analysis. Never call individual data tools separately."
        )
    )
    async def gather_research_context(ticker: str) -> dict:
        """Fetch all research inputs concurrently."""
        ci, fundamentals, news, past_readings, position = await asyncio.gather(
            _check_ci_impl(ticker),
            _fundamental_impl(ticker),
            _get_news_impl(ticker, max_results=5),
            _retrieve_impl(user_id, ticker, n=3),
            _position_pnl_impl(user_id, ticker),
        )
        return {
            "ci": ci,
            "fundamentals": fundamentals,
            "news": news,
            "past_readings": past_readings,
            "position": position,
        }

    return gather_research_context
