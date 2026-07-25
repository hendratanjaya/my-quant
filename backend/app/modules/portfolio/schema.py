from datetime import datetime as DateTime

from pydantic import BaseModel


class PortfolioPositionCreate(BaseModel):
    ticker: str
    lots: int
    avg_price: float


class PortfolioPositionPatch(BaseModel):
    lots: int | None = None
    avg_price: float | None = None


class PortfolioPositionRead(BaseModel):
    ticker: str
    lots: int
    avg_price: float
    created_at: DateTime
    updated_at: DateTime
