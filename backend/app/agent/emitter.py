"""Publish agent lifecycle events to a per-task Redis pubsub channel."""

from __future__ import annotations

import json

from app.core.redis_client import get_redis


class Emitter:
    def __init__(self, task_id: str, prefix: str = "agent"):
        self.task_id = task_id
        self.channel = f"{prefix}:{task_id}"

    def emit(self, event_type: str, data: dict) -> None:
        payload = json.dumps({"type": event_type, "data": data})
        get_redis().publish(self.channel, payload)
