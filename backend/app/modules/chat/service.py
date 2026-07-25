from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.model.database import ChatMessage
from app.modules.chat.schema import ChatMessageRead


async def clear_history(session: AsyncSession, user_id: str) -> None:
    await session.exec(delete(ChatMessage).where(ChatMessage.user_id == user_id))
    await session.commit()


async def list_history(
    session: AsyncSession, user_id: str, limit: int = 50
) -> list[ChatMessageRead]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    rows = (await session.exec(stmt)).all()
    return [
        ChatMessageRead(
            id=r.id or 0,
            role=r.role,
            content=r.content,
            task_id=r.task_id,
            trace_json=r.trace_json,
            created_at=r.created_at,
        )
        for r in rows
    ]
