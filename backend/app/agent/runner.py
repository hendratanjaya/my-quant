"""Celery task that runs an agent turn end-to-end and streams events to Redis."""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime as DateTime

from agents import Runner
from agents.extensions.memory import SQLAlchemySession
from agents.memory.session_settings import SessionSettings
from openai.types.responses import ResponseTextDeltaEvent

from app.agent.agents.orchestrator import build_orchestrator
from app.agent.emitter import Emitter
from app.agent.persistence import persist_reading
from app.core.celery_app import celery_app
from app.model.database import ChatMessage
from app.model.engine import engine, get_session

_TICKER_RE = re.compile(r"\b([A-Z]{4})\b")


def _detect_ticker(text: str) -> str | None:
    match = _TICKER_RE.search(text.upper())
    return match.group(1) if match else None


async def _run_agent_async(task_id: str, user_id: str, message: str) -> dict | None:
    """Stream the agent and collect results. Returns data dict, or None on streaming error.

    Persistence is intentionally excluded — the anyio cancel scope inside the MCP
    stdio client poisons the asyncio Task on cleanup, making every subsequent await
    raise CancelledError. By returning plain data here and persisting in a separate
    asyncio.run() call, we keep the two concerns in clean, isolated event loops.
    """
    started_at = time.time()
    emitter = Emitter(task_id)
    await asyncio.sleep(0.2)  # give SSE endpoint time to subscribe
    emitter.emit("start", {"message": message})

    orchestrator, mcp_servers = await build_orchestrator(user_id)
    session_memory = SQLAlchemySession(
        session_id=user_id,
        engine=engine,
        create_tables=True,
        session_settings=SessionSettings(limit=20),
    )

    buffered_text: list[str] = []
    trace_events: list[dict] = []
    final_agent_name = "Orchestrator"
    stream_ok = True

    try:
        runner = Runner.run_streamed(
            orchestrator,
            input=message,
            session=session_memory,
            max_turns=20,
        )
        async for event in runner.stream_events():
            if event.type == "raw_response_event":
                if isinstance(event.data, ResponseTextDeltaEvent):
                    emitter.emit("token", {"text": event.data.delta})
                    buffered_text.append(event.data.delta)
            elif event.type == "run_item_stream_event":
                if event.name == "tool_called":
                    entry = {
                        "type": "tool_call",
                        "name": event.item.raw_item.name,
                        "args": event.item.raw_item.arguments,
                    }
                    emitter.emit("tool_call", entry)
                    trace_events.append(entry)
                elif event.name == "tool_output":
                    preview = str(event.item.raw_item)[:200]
                    entry = {"type": "tool_result", "preview": preview}
                    emitter.emit("tool_result", entry)
                    trace_events.append(entry)
            elif event.type == "agent_updated_stream_event":
                final_agent_name = event.new_agent.name
                entry = {"type": "handoff", "to": final_agent_name}
                emitter.emit("handoff", entry)
                trace_events.append(entry)
    except Exception as exc:
        emitter.emit("error", {"message": str(exc), "where": "stream"})
        stream_ok = False
    finally:
        for server in mcp_servers:
            try:
                await server.cleanup()
            except BaseException as exc:
                # anyio cancel scope fires here on MCP subprocess teardown.
                # Call uncancel() so Python 3.11+'s _num_cancels_requested counter
                # goes back to zero — otherwise the task is cancelled on StopIteration
                # even though the coroutine returned normally.
                if isinstance(exc, asyncio.CancelledError):
                    task = asyncio.current_task()
                    if task is not None:
                        task.uncancel()

    if not stream_ok:
        return None

    # No awaits past this point — safe return despite prior cancellation noise.
    return {
        "full_text": "".join(buffered_text),
        "trace_events": trace_events,
        "final_agent_name": final_agent_name,
        "started_at": started_at,
    }


async def _persist_and_done(
    task_id: str,
    user_id: str,
    message: str,
    emitter: Emitter,
    data: dict,
) -> None:
    """Persist results and emit done. Runs in a fresh event loop — no anyio poison."""
    full_text = data["full_text"]
    trace_events = data["trace_events"]
    final_agent_name = data["final_agent_name"]
    started_at = data["started_at"]
    detected = _detect_ticker(message)

    reading_id: str | None = None
    if final_agent_name == "Research" and detected:
        reading_id = await persist_reading(
            user_id=user_id,
            ticker=detected,
            body=full_text,
            payload_xml="",
        )

    duration_ms = int((time.time() - started_at) * 1000)
    now = DateTime.utcnow()

    async for session in get_session():
        session.add(
            ChatMessage(
                user_id=user_id,
                role="user",
                content=message,
                task_id=task_id,
                created_at=now,
            )
        )
        session.add(
            ChatMessage(
                user_id=user_id,
                role="assistant",
                content=full_text,
                task_id=task_id,
                trace_json=json.dumps(trace_events),
                created_at=now,
            )
        )
        await session.commit()
        break

    emitter.emit("done", {"reading_id": reading_id, "duration_ms": duration_ms})


@celery_app.task(name="run_agent")
def run_agent(task_id: str, user_id: str, message: str) -> None:
    emitter = Emitter(task_id)

    data: dict | None = None
    try:
        data = asyncio.run(_run_agent_async(task_id, user_id, message))
    except BaseException:
        # Residual CancelledError that escaped despite uncancel() — streaming
        # data is lost; error was already emitted inside _run_agent_async.
        return

    if data is None:
        return  # streaming error already emitted

    # Fresh event loop: no anyio cancel scope state, clean SQLAlchemy connections.
    asyncio.run(_persist_and_done(task_id, user_id, message, emitter, data))
