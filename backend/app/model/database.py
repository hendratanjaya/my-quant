from datetime import datetime as DateTime
from typing import Optional

from sqlmodel import Field, SQLModel


class NewsArticle(SQLModel, table=True):
    """Ingested news item. URL is the dedup key."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: Optional[str] = None
    url: str = Field(unique=True)
    published_at: DateTime
    source: str
    ticker: Optional[str] = Field(default=None, index=True)
    embedding_id: Optional[str] = None


class JournalEntry(SQLModel, table=True):
    """User note, optionally tagged to a ticker."""

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    ticker: Optional[str] = Field(default=None, index=True)
    created_at: DateTime = Field(default_factory=DateTime.utcnow)
    embedding_id: Optional[str] = None


class AlertHistory(SQLModel, table=True):
    """Record of every nightly alert sent."""

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    reason: str
    created_at: DateTime = Field(default_factory=DateTime.utcnow)
    sent_at: Optional[DateTime] = None
