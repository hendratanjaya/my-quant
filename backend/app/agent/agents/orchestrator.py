"""Orchestrator agent: classifies and routes NL chat to Research or Portfolio."""

from __future__ import annotations

from agents import Agent

from app.agent.agents.portfolio import build_portfolio_agent
from app.agent.agents.research import build_research_agent
from app.core.llm_models import analysis_model

ORCHESTRATOR_INSTRUCTIONS = """
You route user messages to a sub-agent. Do NOT answer questions yourself.

- Anything about a specific IDX ticker (BBRI, BBCA, TLKM, etc.) — fundamentals,
  technicals, "how does X look", "should I buy X", "is X strong now" —
  hand off to Research.
- "What do you think of my position in X", "how is my X doing", "should I hold/sell X" —
  even though the user mentions their own position, this is an ANALYSIS request —
  hand off to Research (it fetches their position as part of the parallel gather).
- Pure portfolio queries with no analysis intent — "what do I have", "show my portfolio",
  "how am I doing overall", "list my positions" — hand off to Portfolio.
- Portfolio CRUD requests also go to Portfolio:
  "add X to my porto", "I bought X lots of BBRI", "remove BBRI", "I sold all BBRI",
  "update my BBRI average", "change my lots for TLKM" — all hand off to Portfolio.
- Macro / market-wide questions — IHSG, JCI, "how is the market", "is the market
  bullish", "market outlook", "macro conditions", sector rotations — hand off to Research.
  Research will answer with macro context and pivot to actionable individual stock ideas.
- If a ticker reference is ambiguous ("it", "that stock") and there is no prior
  context, ask the user to name the ticker explicitly.
- Anything genuinely unrelated to Indonesian stocks or markets (e.g. US stocks, crypto,
  forex, general finance trivia) — respond briefly that you focus on IDX analysis only.
"""


async def build_orchestrator(user_id: str) -> tuple[Agent, list]:
    research = build_research_agent(user_id)
    portfolio = build_portfolio_agent(user_id)
    orchestrator = Agent(
        name="Orchestrator",
        model=analysis_model,
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        handoffs=[research, portfolio],
    )
    return orchestrator, []
