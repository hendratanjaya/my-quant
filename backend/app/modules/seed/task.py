"""Celery task: bulk-seed fundamentals for all IDX tickers from Stockbit."""

from __future__ import annotations

import asyncio
import logging

from app.core.celery_app import celery_app
from app.lib.idx_tickers import IDX_TICKERS
from app.model.engine import get_session
from app.modules.seed.service import upsert_ticker
from app.scrapers.stockbit.fetcher import StockbitAuthError

logger = logging.getLogger(__name__)

BATCH_SIZE = 5
BATCH_DELAY = 5.0


async def _bulk_seed_async(jwt: str, limit: int | None = None) -> None:
    tickers = IDX_TICKERS[:limit] if limit else IDX_TICKERS
    total = len(tickers)
    total_batches = -(-total // BATCH_SIZE)

    async def seed_one(symbol: str):
        async for session in get_session():
            await upsert_ticker(symbol, jwt, session)
            break
        return symbol

    for batch_num, i in enumerate(range(0, total, BATCH_SIZE), start=1):
        batch = tickers[i : i + BATCH_SIZE]
        ok = []
        for symbol in batch:
            try:
                await seed_one(symbol)
                ok.append(symbol)
            except StockbitAuthError:
                logger.error("bulk_seed: JWT expired — aborting at batch %d/%d", batch_num, total_batches)
                return
            except Exception as e:
                logger.warning("bulk_seed: %s failed — %s", symbol, e)

        logger.info("bulk_seed: batch %d/%d — %s", batch_num, total_batches, ", ".join(ok))

        if i + BATCH_SIZE < total:
            await asyncio.sleep(BATCH_DELAY)

    logger.info("bulk_seed: done — %d tickers processed", total)


@celery_app.task(name="bulk_seed_fundamentals", time_limit=1800, soft_time_limit=1700)
def bulk_seed_fundamentals(jwt: str, limit: int | None = None) -> None:
    asyncio.run(_bulk_seed_async(jwt, limit=limit))
