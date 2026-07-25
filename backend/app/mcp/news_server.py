"""news-mcp: fresh Indonesian financial news via DuckDuckGo. stdio transport."""

from __future__ import annotations

from ddgs import DDGS
from openai import AsyncOpenAI

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("news-mcp")

_QUERY_MODEL = "deepseek/deepseek-v4-flash"
_OR_BASE = "https://openrouter.ai/api/v1"

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        from app.core.settings import settings

        _client = AsyncOpenAI(api_key=settings.open_router_key, base_url=_OR_BASE)
    return _client


async def _generate_query(symbol: str) -> str:
    """Ask deepseek-v4-flash for one optimised DuckDuckGo query."""
    try:
        res = await _get_client().chat.completions.create(
            model=_QUERY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate search queries for Indonesian stock news. "
                        "Respond with ONLY the search query — no explanation, no quotes, no punctuation at the end."
                    ),
                },
                {
                    "role": "user",
                    "content": f"One search query for the latest financial news about {symbol.upper()} on the IDX (Indonesian stock exchange).",
                },
            ],
            max_tokens=60,
        )
        query = (res.choices[0].message.content or "").strip().strip('"').strip("'")
        return query or f"{symbol.upper()} saham IDX"
    except Exception:
        return f"{symbol.upper()} saham IDX"


async def _get_news_impl(symbol: str, max_results: int = 5) -> list[dict]:
    query = await _generate_query(symbol)
    try:
        with DDGS() as ddgs:
            raw = ddgs.news(query, max_results=max_results, region="id-id") or []
    except Exception:
        raw = []
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "date": r.get("date", ""),
            "source": r.get("source", ""),
            "snippet": r.get("body", ""),
            "query": query,
        }
        for r in raw
    ]


@mcp.tool(
    description=(
        "Fetch the latest Indonesian financial news for an IDX ticker. "
        "Internally generates an optimised search query then searches DuckDuckGo. "
        "Returns items with title, url, date, source, snippet, and the query used. "
        "Always include the urls as markdown links in your response."
    )
)
async def get_news(symbol: str, max_results: int = 5) -> list[dict]:
    return await _get_news_impl(symbol, max_results)


if __name__ == "__main__":
    mcp.run()
