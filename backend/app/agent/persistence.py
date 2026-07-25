"""Write-back path for finished agent runs: SQLite + Chroma."""

from __future__ import annotations

import uuid
from datetime import datetime as DateTime

from app.core.chroma_client import AGENT_READINGS_COLLECTION, get_chroma
from app.core.llm_models import EMBED_MODEL, embed_client
from app.model.database import AgentReading
from app.model.engine import get_session


async def _embed(texts: list[str]) -> list[list[float]]:
    res = await embed_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in res.data]


async def persist_reading(
    user_id: str, ticker: str, body: str, payload_xml: str
) -> str:
    reading_id = str(uuid.uuid4())
    ticker_up = ticker.upper()
    created_at = DateTime.utcnow()

    async for session in get_session():
        session.add(
            AgentReading(
                id=reading_id,
                user_id=user_id,
                ticker=ticker_up,
                body=body,
                payload_xml=payload_xml,
                created_at=created_at,
            )
        )
        await session.commit()
        break

    embeddings = await _embed([body])
    collection = get_chroma().get_or_create_collection(AGENT_READINGS_COLLECTION)
    collection.add(
        ids=[reading_id],
        documents=[body],
        embeddings=embeddings,
        metadatas=[
            {
                "user_id": user_id,
                "ticker": ticker_up,
                "created_at": created_at.isoformat(),
            }
        ],
    )
    return reading_id
