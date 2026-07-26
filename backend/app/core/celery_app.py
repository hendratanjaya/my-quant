"""Celery app factory. Broker + result backend both use Redis."""

from __future__ import annotations

from agents.tracing import set_tracing_disabled
from celery import Celery

from app.core.settings import settings

set_tracing_disabled(True)

celery_app = Celery(
    "my_quant",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.agent.runner",
        "app.modules.screen.task",
        "app.modules.seed.task",
        "app.modules.telegram.task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_time_limit=180,
    task_soft_time_limit=150,
)
