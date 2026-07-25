"""Retrieve past agent readings from Chroma, scoped by user + ticker."""

from __future__ import annotations

from agents import function_tool

from app.core.chroma_client import AGENT_READINGS_COLLECTION, get_chroma
from app.core.llm_models import EMBED_MODEL, embed_client


async def _embed(texts: list[str]) -> list[list[float]]:
    res = await embed_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in res.data]


async def _retrieve_impl(user_id: str, ticker: str, n: int = 3) -> list[dict]:
    ticker_up = ticker.upper()
    collection = get_chroma().get_or_create_collection(AGENT_READINGS_COLLECTION)
    if collection.count() == 0:
        return []
    embedding = (await _embed([f"analysis of {ticker_up}"]))[0]
    results = collection.query(
        query_embeddings=[embedding],
        where={"$and": [{"user_id": user_id}, {"ticker": ticker_up}]},
        n_results=n,
    )
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    return [
        {"body": doc, "created_at": meta.get("created_at")}
        for doc, meta in zip(documents, metadatas)
    ]


def make_retrieve_tool(user_id: str):
    @function_tool(
        description_override=(
            "Return up to N past agent readings for a given ticker (scoped to "
            "this user). Call this BEFORE writing any new analysis so you can "
            "reference how the thesis has evolved. Returns [] on day 1 — that's "
            "fine, just skip the past-readings section of your XML payload."
        )
    )
    async def retrieve_past_readings(ticker: str, n: int = 3) -> list[dict]:
        return await _retrieve_impl(user_id, ticker, n)

    return retrieve_past_readings
