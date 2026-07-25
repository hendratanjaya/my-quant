import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.redis_client import get_async_redis
from app.model.engine import get_session
from app.modules.chat import service
from app.modules.chat.schema import (
    ChatDispatchResponse,
    ChatMessagePayload,
    ChatMessageRead,
)

router = APIRouter(tags=["chat"])


def _require_user_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header required")
    return x_user_id


@router.post("/api/agent/chat", response_model=ChatDispatchResponse)
async def dispatch_chat(
    payload: ChatMessagePayload,
    user_id: str = Depends(_require_user_id),
):
    from app.agent.runner import run_agent

    task_id = str(uuid.uuid4())
    run_agent.delay(task_id, user_id, payload.message)
    return ChatDispatchResponse(task_id=task_id)


@router.get("/api/agent/stream/{task_id}")
async def stream_chat(
    task_id: str,
    user_id: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
):
    resolved = x_user_id or user_id
    if not resolved:
        raise HTTPException(status_code=400, detail="user_id required")
    channel = f"agent:{task_id}"

    async def gen():
        r = get_async_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for msg in pubsub.listen():
                if msg["type"] != "message":
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
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/api/chat/history", response_model=list[ChatMessageRead])
async def history(
    limit: int = 50,
    user_id: str = Depends(_require_user_id),
    session=Depends(get_session),
):
    return await service.list_history(session, user_id, limit)


@router.delete("/api/chat/history", status_code=204)
async def clear_history(
    user_id: str = Depends(_require_user_id),
    session=Depends(get_session),
):
    await service.clear_history(session, user_id)
