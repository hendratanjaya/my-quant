from datetime import datetime as DateTime

from pydantic import BaseModel


class ChatMessagePayload(BaseModel):
    message: str


class ChatDispatchResponse(BaseModel):
    task_id: str


class ChatMessageRead(BaseModel):
    id: int
    role: str
    content: str
    task_id: str | None
    trace_json: str | None
    created_at: DateTime
