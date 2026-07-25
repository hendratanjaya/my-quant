from fastapi import APIRouter, Depends

from app.model.engine import get_session
from app.modules.fundamental.schema import FundamentalReport
from app.modules.fundamental.service import get_fundamental_report

router = APIRouter(prefix="/api/fundamental", tags=["fundamental"])


@router.get("/{symbol}", response_model=FundamentalReport)
async def get_fundamental(
    symbol: str, session=Depends(get_session)
) -> FundamentalReport:
    return await get_fundamental_report(symbol, session)
