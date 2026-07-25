"""Fundamental snapshot function tool for the Research sub-agent."""

from __future__ import annotations

from agents import function_tool

from app.model.engine import get_session
from app.modules.fundamental.service import get_fundamental_report


@function_tool(
    description_override=(
        "Return the computed 10-year fundamental snapshot for an IDX ticker: "
        "percentile-ranked metrics (PBV, PER, ROE, NPM, etc.), quarterly series, "
        "and derived TTM values. Call this before commenting on a company's "
        "fundamentals in an analysis."
    )
)
async def get_fundamental_snapshot(symbol: str) -> dict:
    """Return the fundamental report for `symbol` as a JSON-serializable dict."""
    async for session in get_session():
        report = await get_fundamental_report(symbol, session)
        return report.model_dump(mode="json")
    return {}
