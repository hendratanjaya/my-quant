"""Celery task: screen all IDX tickers for CI signals concurrently."""

from __future__ import annotations

import asyncio

from app.agent.emitter import Emitter
from app.core.celery_app import celery_app
from app.lib.ci_system import compute
from app.lib.idx_tickers import IDX_TICKERS
from app.modules.ohlcv.service import fetch_candles

_VALID_SIGNALS = {"ketat", "superketat", "theone", "kamehameha"}
_CONCURRENCY = 10


async def _screen_async(task_id: str, signals: list[str]) -> None:
    emitter = Emitter(task_id, prefix="screen")
    emitter.emit("start", {"total": len(IDX_TICKERS), "signals": signals})

    sem = asyncio.Semaphore(_CONCURRENCY)
    hit_count = 0

    async def check_one(ticker: str) -> None:
        nonlocal hit_count
        async with sem:
            try:
                candles = await fetch_candles(ticker, 730)
                result = compute(ticker, candles)
                matched = [s for s in signals if result["ci_signals"].get(s)]
                if matched:
                    hit_count += 1
                    emitter.emit(
                        "hit",
                        {
                            "ticker": ticker,
                            "signals": matched,
                            "price": result["price"],
                            "volume_ratio": result["volume_ratio"],
                            "momentum_5d_pct": result["momentum_5d_pct"],
                        },
                    )
            except Exception:
                pass  # skip tickers with no data

    await asyncio.gather(*[check_one(t) for t in IDX_TICKERS])
    emitter.emit("done", {"count": hit_count})


@celery_app.task(name="run_screen", time_limit=600, soft_time_limit=570)
def run_screen(task_id: str, signals: list[str]) -> None:
    asyncio.run(_screen_async(task_id, signals))
