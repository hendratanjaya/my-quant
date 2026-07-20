"""Stockbit HTTP client — reads a caller-supplied JWT, calls the financial endpoint."""

from __future__ import annotations

from typing import Literal

import httpx

STOCKBIT_URL = "https://exodus.stockbit.com/findata-view/company/financial"

_COMMON_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"
    ),
    "Referer": "https://stockbit.com/",
    "Origin": "https://stockbit.com",
}


class StockbitAuthError(Exception):
    """Raised when Stockbit responds 401 — JWT expired or invalid."""


class StockbitFetchError(Exception):
    """Non-auth upstream failure (5xx, network, non-JSON body, etc.)."""


async def fetch_financial(
    symbol: str,
    jwt: str,
    report_type: Literal[1, 2, 3] = 1,
    data_type: int = 1,
    statement_type: int = 1,
) -> dict:
    """Fetch one financial statement. Returns the raw JSON payload."""
    params = {
        "symbol": symbol.upper(),
        "data_type": data_type,
        "report_type": report_type,
        "statement_type": statement_type,
    }
    headers = {**_COMMON_HEADERS, "Authorization": f"Bearer {jwt}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(STOCKBIT_URL, params=params, headers=headers)

    if r.status_code == 401:
        raise StockbitAuthError()
    if not r.is_success:
        raise StockbitFetchError(f"upstream {r.status_code}: {r.text[:200]}")

    try:
        return r.json()
    except ValueError as exc:
        raise StockbitFetchError(f"invalid JSON from upstream: {exc}") from exc
