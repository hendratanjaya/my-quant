from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.model.engine import get_session
from app.modules.portfolio import service
from app.modules.portfolio.schema import (
    PortfolioPositionCreate,
    PortfolioPositionPatch,
    PortfolioPositionRead,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _require_user_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header required")
    return x_user_id


@router.get("", response_model=list[PortfolioPositionRead])
async def list_positions(
    user_id: str = Depends(_require_user_id),
    session=Depends(get_session),
):
    return await service.list_positions(session, user_id)


@router.post(
    "", response_model=PortfolioPositionRead, status_code=status.HTTP_201_CREATED
)
async def add_position(
    payload: PortfolioPositionCreate,
    user_id: str = Depends(_require_user_id),
    session=Depends(get_session),
):
    try:
        return await service.add_position(session, user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{ticker}", response_model=PortfolioPositionRead)
async def update_position(
    ticker: str,
    patch: PortfolioPositionPatch,
    user_id: str = Depends(_require_user_id),
    session=Depends(get_session),
):
    try:
        return await service.update_position(session, user_id, ticker, patch)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    ticker: str,
    user_id: str = Depends(_require_user_id),
    session=Depends(get_session),
):
    await service.delete_position(session, user_id, ticker)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
