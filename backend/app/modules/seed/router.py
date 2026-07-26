import json
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import select

from app.lib.idx_tickers import IDX_TICKERS
from app.model.database import FundamentalDataRow
from app.model.engine import get_session
from app.modules.seed import service
from app.modules.seed.schema import SeededSummary, SeededTicker
from app.modules.seed.task import bulk_seed_fundamentals
from app.scrapers.stockbit.fetcher import StockbitAuthError, StockbitFetchError

router = APIRouter(prefix="/api/seed", tags=["seed"])

_SEED_FILE = Path("data/seeded.json")


@router.post("/from-file", response_model=list[SeededSummary], status_code=200)
async def import_from_file(session=Depends(get_session)) -> list[SeededSummary]:
    """Import all tickers from seeded.json into the database. Skips tickers that already have rows."""
    if not _SEED_FILE.exists():
        raise HTTPException(status_code=404, detail=f"{_SEED_FILE} not found")

    raw = json.loads(_SEED_FILE.read_text())
    store = {sym: SeededTicker.model_validate(payload) for sym, payload in raw.items()}

    symbols_with_rows = set(
        (await session.exec(select(FundamentalDataRow.symbol).distinct())).all()
    )

    for symbol, ticker in store.items():
        if symbol in symbols_with_rows:
            continue
        for row in ticker.rows:
            session.add(
                FundamentalDataRow(
                    symbol=symbol,
                    period_end=row.period_end,
                    metric=row.metric,
                    value=row.value,
                )
            )

    await session.commit()
    return await service.list_summaries(session)


@router.post("/bulk", status_code=202)
def bulk_seed(
    authorization: str | None = Header(default=None),
    limit: int | None = None,
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    jwt = authorization.removeprefix("Bearer ").strip()
    total = min(limit, len(IDX_TICKERS)) if limit else len(IDX_TICKERS)
    bulk_seed_fundamentals.delay(jwt, limit=limit)
    return {"status": "queued", "total": total}


@router.get("", response_model=list[SeededSummary])
async def list_seeded(session=Depends(get_session)) -> list[SeededSummary]:
    return await service.list_summaries(session)


@router.post("/{symbol}", response_model=SeededSummary, status_code=201)
async def seed_ticker(
    symbol: str,
    authorization: str | None = Header(default=None),
    session=Depends(get_session),
) -> SeededSummary:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    jwt = authorization.removeprefix("Bearer ").strip()

    try:
        return await service.seed_ticker(symbol, jwt, session)
    except service.AlreadySeededError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StockbitAuthError as exc:
        raise HTTPException(
            status_code=401, detail="Stockbit JWT invalid or expired"
        ) from exc
    except StockbitFetchError as exc:
        raise HTTPException(
            status_code=502, detail=f"Stockbit upstream error: {exc}"
        ) from exc
