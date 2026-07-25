"""Celery task: screen all IDX tickers and push results to Telegram."""

from __future__ import annotations

import asyncio

from app.core.celery_app import celery_app
from app.lib.ci_system import compute
from app.lib.idx_tickers import IDX_TICKERS
from app.lib.telegram import send_message
from app.modules.ohlcv.service import fetch_candles

_CONCURRENCY = 10


async def _screen_async(chat_id: int, signals: list[str]) -> None:
    sem = asyncio.Semaphore(_CONCURRENCY)
    hits: list[dict] = []

    async def check_one(ticker: str) -> None:
        async with sem:
            try:
                candles = await fetch_candles(ticker, 730)
                result = compute(ticker, candles)
                matched = [s for s in signals if result["ci_signals"].get(s)]
                if matched:
                    hits.append(
                        {
                            "ticker": ticker,
                            "signals": matched,
                            "volume_ratio": result["volume_ratio"],
                            "momentum_5d_pct": result["momentum_5d_pct"],
                        }
                    )
            except Exception:
                pass

    await asyncio.gather(*[check_one(t) for t in IDX_TICKERS])

    if not hits:
        send_message(chat_id, "No tickers matched the selected signals.")
        return

    sig_label = ", ".join(s.upper() for s in signals)
    send_message(
        chat_id,
        f"<b>Screener — {sig_label}</b>  {len(hits)} result{'s' if len(hits) != 1 else ''}",
    )

    col_header = f"{'TICKER':<7} {'SIGNAL':<12} {'VOL':>6}  {'MOM':>7}"
    divider = "-" * len(col_header)
    rows = [col_header, divider]
    for h in hits:
        vol = f"{h['volume_ratio']:.2f}x" if h["volume_ratio"] is not None else "-"
        mom_val = h["momentum_5d_pct"]
        mom = (
            (f"+{mom_val:.2f}%" if mom_val >= 0 else f"{mom_val:.2f}%")
            if mom_val is not None
            else "-"
        )
        sigs = ", ".join(h["signals"])
        rows.append(f"{h['ticker']:<7} {sigs:<12} {vol:>6}  {mom:>7}")

    # Send in chunks of 50 rows, each as a self-contained <pre> block
    CHUNK = 50
    for i in range(0, len(rows), CHUNK):
        block = "\n".join(rows[i : i + CHUNK])
        send_message(chat_id, f"<pre>{block}</pre>")


@celery_app.task(name="run_screen_telegram")
def run_screen_telegram(chat_id: int, signals: list[str]) -> None:
    try:
        asyncio.run(_screen_async(chat_id, signals))
    except Exception as e:
        send_message(chat_id, f"Screener error: {e}")
