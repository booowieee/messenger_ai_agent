from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import WhitelistChat
from src.database.connection import redis_client
from src.utils.logger import export_logger as logger

REDIS_WHITELIST_PREFIX = "whitelist:chat:"


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_whitelisted(self, chat_id: int) -> bool:
        redis_key = f"{REDIS_WHITELIST_PREFIX}{chat_id}"
        cached_val = await redis_client.get(redis_key)
        if cached_val is not None:
            return cached_val == "1"

        result = await self.session.execute(
            select(WhitelistChat).where(
                WhitelistChat.chat_id == chat_id,
                WhitelistChat.is_active == True
            )
        )
        chat = result.scalar_one_or_none()
        is_active = chat is not None
        
        await redis_client.set(redis_key, "1" if is_active else "0", ex=3600)
        return is_active

    async def add_to_whitelist(self, chat_id: int, chat_title: str, username: Optional[str] = None) -> WhitelistChat:
        result = await self.session.execute(
            select(WhitelistChat).where(WhitelistChat.chat_id == chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.is_active = True
            chat.chat_title = chat_title
            chat.username = username
        else:
            chat = WhitelistChat(
                chat_id=chat_id,
                chat_title=chat_title,
                username=username,
                is_active=True
            )
            self.session.add(chat)

        await self.session.commit()
        await self.session.refresh(chat)

        redis_key = f"{REDIS_WHITELIST_PREFIX}{chat_id}"
        await redis_client.set(redis_key, "1", ex=3600)
        logger.info(f"Chat {chat_id} ({chat_title}) added to whitelist.")
        return chat

    async def remove_from_whitelist(self, chat_id: int) -> bool:
        result = await self.session.execute(
            select(WhitelistChat).where(WhitelistChat.chat_id == chat_id)
        )
        chat = result.scalar_one_or_none()
        if chat:
            chat.is_active = False
            await self.session.commit()
            
            redis_key = f"{REDIS_WHITELIST_PREFIX}{chat_id}"
            await redis_client.set(redis_key, "0", ex=3600)
            logger.info(f"Chat {chat_id} removed from whitelist.")
            return True
        return False

    async def list_active_chats(self) -> List[WhitelistChat]:
        result = await self.session.execute(
            select(WhitelistChat).where(WhitelistChat.is_active == True).order_by(WhitelistChat.created_at.desc())
        )
        return list(result.scalars().all())
