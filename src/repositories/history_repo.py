from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ChatSummary, MessageHistory


class HistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_message(self, chat_id: int, sender: str, text: str) -> MessageHistory:
        msg = MessageHistory(
            chat_id=chat_id,
            sender=sender,  # 'user' or 'model'
            text=text
        )
        self.session.add(msg)
        await self.session.commit()
        return msg

    async def get_recent_history(self, chat_id: int, limit: int = 15) -> List[MessageHistory]:
        result = await self.session.execute(
            select(MessageHistory)
            .where(MessageHistory.chat_id == chat_id)
            .order_by(MessageHistory.created_at.desc())
            .limit(limit)
        )
        # Reverse to get chronological order (oldest -> newest)
        return list(reversed(result.scalars().all()))

    async def get_summary(self, chat_id: int) -> Optional[str]:
        result = await self.session.execute(
            select(ChatSummary).where(ChatSummary.chat_id == chat_id)
        )
        obj = result.scalar_one_or_none()
        return obj.summary if obj else None

    async def save_summary(self, chat_id: int, summary_text: str) -> ChatSummary:
        result = await self.session.execute(
            select(ChatSummary).where(ChatSummary.chat_id == chat_id)
        )
        obj = result.scalar_one_or_none()
        if obj:
            obj.summary = summary_text
        else:
            obj = ChatSummary(chat_id=chat_id, summary=summary_text)
            self.session.add(obj)
        await self.session.commit()
        return obj
