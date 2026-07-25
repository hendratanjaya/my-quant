"""Chroma client singleton, initialized lazily on first access."""

from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.settings import settings

AGENT_READINGS_COLLECTION = "agent_readings"

_client: chromadb.PersistentClient | None = None


def get_chroma() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Ensure the readings collection exists.
        _client.get_or_create_collection(AGENT_READINGS_COLLECTION)
    return _client
