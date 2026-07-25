from datetime import date as Date
from datetime import datetime as DateTime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class JournalEntry(SQLModel, table=True):
    """User note, optionally tagged to a ticker. Dormant until v2 /note UX ships."""

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    ticker: Optional[str] = Field(default=None, index=True)
    created_at: DateTime = Field(default_factory=DateTime.utcnow)
    embedding_id: Optional[str] = None


class AlertHistory(SQLModel, table=True):
    """Record of nightly alerts. Dormant until v2 alerts ship."""

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    reason: str
    created_at: DateTime = Field(default_factory=DateTime.utcnow)
    sent_at: Optional[DateTime] = None


class PortfolioPosition(SQLModel, table=True):
    __tablename__ = "portfolio_positions"
    __table_args__ = (UniqueConstraint("user_id", "ticker"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    ticker: str = Field(index=True)
    lots: int
    avg_price: float
    created_at: DateTime = Field(default_factory=DateTime.utcnow)
    updated_at: DateTime = Field(default_factory=DateTime.utcnow)


class AgentReading(SQLModel, table=True):
    __tablename__ = "agent_readings"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    ticker: str = Field(index=True)
    body: str
    payload_xml: str
    created_at: DateTime = Field(default_factory=DateTime.utcnow, index=True)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    role: str
    content: str
    task_id: Optional[str] = None
    trace_json: Optional[str] = None
    created_at: DateTime = Field(default_factory=DateTime.utcnow, index=True)


class FundamentalDataRow(SQLModel, table=True):
    __tablename__ = "fundamental_rows"
    __table_args__ = (UniqueConstraint("symbol", "period_end", "metric"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    period_end: Date = Field(index=True)
    metric: str
    value: float
