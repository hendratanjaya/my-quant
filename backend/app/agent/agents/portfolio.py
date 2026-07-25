"""Portfolio sub-agent: answers 'how am I doing' from the user's SQLite positions."""

from __future__ import annotations

from agents import Agent

from app.agent.tools.portfolio import make_portfolio_tools
from app.core.llm_models import analysis_model

PORTFOLIO_INSTRUCTIONS = """
You manage the user's IDX stock portfolio. You have five tools:

- get_portfolio() — list all positions
- get_position_pnl(ticker) — current P&L for one position
- add_position(ticker, lots, avg_price) — add a new holding
- update_position(ticker, lots?, avg_price?) — update lots or avg price
- delete_position(ticker) — remove a holding entirely

CRUD rules:
- "add BBRI, 10 lots, avg 3000" → add_position("BBRI", 10, 3000)
- "I bought 5 more BBRI at 3200" → first check if BBRI exists; if yes, update lots/avg_price; if no, add it
- "I sold all my BBRI" → delete_position("BBRI")
- "update my BBRI avg to 3100" → update_position("BBRI", avg_price=3100)

Always confirm what you did with the actual values stored. Be concise.
Do NOT give buy/sell recommendations — that's the Research agent's job.
"""


def build_portfolio_agent(user_id: str) -> Agent:
    get_portfolio, get_position_pnl, add_position, update_position, delete_position = (
        make_portfolio_tools(user_id)
    )
    return Agent(
        name="Portfolio",
        model=analysis_model,
        instructions=PORTFOLIO_INSTRUCTIONS,
        tools=[
            get_portfolio,
            get_position_pnl,
            add_position,
            update_position,
            delete_position,
        ],
    )
