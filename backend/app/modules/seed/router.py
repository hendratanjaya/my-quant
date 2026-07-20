from fastapi import APIRouter, Header, HTTPException

from app.modules.seed import service
from app.modules.seed.schema import SeededSummary
from app.scrapers.stockbit.fetcher import StockbitAuthError, StockbitFetchError

router = APIRouter(prefix="/api/seed", tags=["seed"])


@router.get("", response_model=list[SeededSummary])
def list_seeded() -> list[SeededSummary]:
    return service.list_summaries()


@router.post("/{symbol}", response_model=SeededSummary, status_code=201)
async def seed_ticker(
    symbol: str,
    authorization: str | None = Header(default=None),
) -> SeededSummary:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    jwt = authorization.removeprefix("Bearer ").strip()

    try:
        return await service.seed_ticker(symbol, jwt)
    except service.AlreadySeededError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StockbitAuthError as exc:
        raise HTTPException(status_code=401, detail="Stockbit JWT invalid or expired") from exc
    except StockbitFetchError as exc:
        raise HTTPException(status_code=502, detail=f"Stockbit upstream error: {exc}") from exc
