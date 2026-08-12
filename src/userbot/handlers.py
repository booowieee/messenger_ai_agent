import asyncio
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from src.database.connection import async_session_factory
from src.repositories.chat_repo import ChatRepository
from src.repositories.settings_repo import SettingsRepository
from src.services.agent_service import AgentService
from src.services.context_service import ContextService
from src.utils.human_delay import simulate_human_response_delay
from src.utils.logger import export_logger as logger

# Блокировки для предотвращения конкурентных ответов в одном чате
_chat_locks: dict[int, asyncio.Lock] = {}


def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


async def handle_incoming_private_message(app: Client, message: Message):
    if message.outgoing or (message.from_user and message.from_user.is_self):
        return

    if not message.text or message.text.startswith("/"):
        return

    chat_id = message.chat.id
    user_text = message.text
    user_name = message.chat.first_name or message.chat.title or "User"

    logger.info(f"Userbot received message in chat {chat_id} ({user_name}): '{user_text}'")

    # Проверка глобальных настроек и белого списка
    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        chat_repo = ChatRepository(session)

        ai_enabled = await settings_repo.is_ai_enabled()
        if not ai_enabled:
            logger.info(f"Message from chat {chat_id} ignored: AI toggle is OFF.")
            return

        whitelist_only = await settings_repo.is_whitelist_only()
        if whitelist_only:
            is_whitelisted = await chat_repo.is_whitelisted(chat_id)
            if not is_whitelisted:
                logger.info(f"Message from chat {chat_id} ignored: Not in whitelist.")
                return
        else:
            logger.info(f"Responding in global mode to chat {chat_id}.")

    # Блокировка чата на время генерации ответа
    lock = _get_chat_lock(chat_id)
    async with lock:
        ai_response = None
        async with async_session_factory() as session:
            agent_service = AgentService(session)
            ai_response = await agent_service.generate_response(chat_id, user_text)

        if not ai_response:
            logger.warning(f"No AI response generated for chat {chat_id}")
            return

        try:
            await simulate_human_response_delay(app, chat_id, text_length=len(ai_response))
            await app.send_message(chat_id, ai_response)
            logger.info(f"Userbot sent AI response to chat {chat_id}")

            # Записываем ответ в историю только при успешной доставке
            async with async_session_factory() as session:
                context_service = ContextService(session)
                await context_service.record_model_message(chat_id, ai_response)

        except FloodWait as e:
            logger.warning(f"FloodWait {e.value}s in chat {chat_id}. Message not saved.")
        except Exception as e:
            logger.exception(f"Error sending message to chat {chat_id}: {e}")


def register_userbot_handlers(client: Client):
    client.add_handler(MessageHandler(handle_incoming_private_message, filters.private), group=0)
    logger.info("Userbot handlers registered.")
