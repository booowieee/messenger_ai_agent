from pyrogram import filters
from pyrogram.types import Message
from src.database.connection import async_session_factory
from src.repositories.chat_repo import ChatRepository
from src.repositories.settings_repo import SettingsRepository
from src.utils.logger import export_logger as logger


async def custom_ai_active_filter(_, __, message: Message) -> bool:
    """Filter that checks if global AI toggle is active and chat is in Whitelist."""
    if not message.chat or not message.text:
        return False

    # Ignore self/outgoing messages and command triggers
    if message.outgoing or (message.from_user and message.from_user.is_self):
        return False

    if message.text.startswith("/"):
        return False

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        chat_repo = ChatRepository(session)

        # 1. Check Global AI Toggle
        ai_enabled = await settings_repo.is_ai_enabled()
        if not ai_enabled:
            logger.info(f"Incoming message from chat {message.chat.id} ignored: Global AI toggle is OFF.")
            return False

        # 2. Check Whitelist
        is_whitelisted = await chat_repo.is_whitelisted(message.chat.id)
        if not is_whitelisted:
            logger.info(f"Incoming message from chat {message.chat.id} ({message.chat.first_name or 'User'}) IGNORED: Chat ID {message.chat.id} is NOT in Whitelist. Please add chat ID {message.chat.id} to Whitelist in Control Bot.")
            return False

        return True


ai_active_filter = filters.create(custom_ai_active_filter)
