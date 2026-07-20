from fastapi import APIRouter

from app.modules.fundamental.schema import FundamentalReport
from app.modules.fundamental.service import get_fundamental_report

router = APIRouter(prefix="/api/fundamental", tags=["fundamental"])


@router.get("/{symbol}", response_model=FundamentalReport)
def get_fundamental(symbol: str) -> FundamentalReport:
    """Return a mock 10-year fundamental report for `symbol`.

    Real values (from the local SQLite archive) and the Research-agent-generated
    reading replace this once ingestion + agent phases land.
    """
    return get_fundamental_report(symbol)
