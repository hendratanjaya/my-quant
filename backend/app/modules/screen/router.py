from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.redis_client import get_redis
from app.modules.screen.task import _VALID_SIGNALS, run_screen

router = APIRouter(tags=["screen"])


def _require_user_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header required")
    return x_user_id


class ScreenPayload(BaseModel):
    signals: list[str]


class ScreenDispatchResponse(BaseModel):
    task_id: str


@router.post("/api/screen", response_model=ScreenDispatchResponse)
async def dispatch_screen(
    payload: ScreenPayload,
    user_id: str = Depends(_require_user_id),
):
    signals = [s.lower() for s in payload.signals if s.lower() in _VALID_SIGNALS]
    if not signals:
        raise HTTPException(
            status_code=400,
            detail=f"No valid signals. Choose from: {', '.join(sorted(_VALID_SIGNALS))}",
        )
    task_id = str(uuid.uuid4())
    run_screen.delay(task_id, signals)
    return ScreenDispatchResponse(task_id=task_id)


@router.get("/api/screen/stream/{task_id}")
async def stream_screen(
    task_id: str,
    user_id: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
):
    if not (x_user_id or user_id):
        raise HTTPException(status_code=400, detail="user_id required")
    channel = f"screen:{task_id}"

    async def gen():
        r = get_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(channel)
        try:
            while True:
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg is None:
                    await asyncio.sleep(0.05)
                    continue
                raw = msg["data"]
                if isinstance(raw, bytes):
                    raw = raw.decode()
                yield f"data: {raw}\n\n"
                try:
                    envelope = json.loads(raw)
                    if envelope.get("type") in ("done", "error"):
                        break
                except json.JSONDecodeError:
                    pass
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(gen(), media_type="text/event-stream")
