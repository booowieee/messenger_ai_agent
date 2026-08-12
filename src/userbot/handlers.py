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

# Блокировки и буферы для накопления сообщений (debounce)
_chat_locks: dict[int, asyncio.Lock] = {}
_pending_messages: dict[int, list[str]] = {}
_debounce_tasks: dict[int, asyncio.Task] = {}


def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


async def process_accumulated_messages_task(chat_id: int, app: Client, user_name: str):
    """Ожидает тишины от собеседника и запускает генерацию ответа."""
    try:
        # Ждем 3.5 секунды тишины от собеседника
        await asyncio.sleep(3.5)
    except asyncio.CancelledError:
        # Собеседник прислал еще сообщение, задача отменена
        return

    # Забираем накопленные сообщения из буфера
    messages = _pending_messages.pop(chat_id, [])
    if not messages:
        return

    combined_text = "\n".join(messages)
    logger.info(f"Userbot processing accumulated messages in chat {chat_id} ({user_name}): '{combined_text}'")

    lock = _get_chat_lock(chat_id)
    try:
        async with lock:
            ai_response = None
            async with async_session_factory() as session:
                agent_service = AgentService(session)
                ai_response = await agent_service.generate_response(chat_id, combined_text)

            if not ai_response:
                logger.warning(f"No AI response generated for chat {chat_id}")
                return

            try:
                # Симулируем человеческую задержку перед прочтением, прочтение и набор
                await simulate_human_response_delay(app, chat_id, text_length=len(ai_response))
                await app.send_message(chat_id, ai_response)
                logger.info(f"Userbot sent AI response to chat {chat_id}")

                async with async_session_factory() as session:
                    context_service = ContextService(session)
                    await context_service.record_model_message(chat_id, ai_response)

            except FloodWait as e:
                logger.warning(f"FloodWait {e.value}s in chat {chat_id}. Message not saved.")
            except Exception as e:
                logger.exception(f"Error sending message to chat {chat_id}: {e}")
                
    except asyncio.CancelledError:
        # Если задача отменена во время ожидания лока, возвращаем сообщения обратно в буфер
        if messages:
            if chat_id not in _pending_messages:
                _pending_messages[chat_id] = []
            _pending_messages[chat_id] = messages + _pending_messages[chat_id]
        raise


async def handle_incoming_private_message(app: Client, message: Message):
    if message.outgoing or (message.from_user and message.from_user.is_self):
        return

    if not message.text or message.text.startswith("/"):
        return

    chat_id = message.chat.id
    user_text = message.text
    user_name = message.chat.first_name or message.chat.title or "User"

    # Быстрая проверка прав, чтобы отсечь сообщения не из белого списка
    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        chat_repo = ChatRepository(session)

        ai_enabled = await settings_repo.is_ai_enabled()
        if not ai_enabled:
            return

        whitelist_only = await settings_repo.is_whitelist_only()
        if whitelist_only:
            is_whitelisted = await chat_repo.is_whitelisted(chat_id)
            if not is_whitelisted:
                return

    # Добавляем входящее сообщение в накопительный буфер чата
    if chat_id not in _pending_messages:
        _pending_messages[chat_id] = []
    _pending_messages[chat_id].append(user_text)

    # Перезапускаем таймер ожидания (debounce)
    old_task = _debounce_tasks.get(chat_id)
    if old_task and not old_task.done():
        old_task.cancel()

    new_task = asyncio.create_task(process_accumulated_messages_task(chat_id, app, user_name))
    _debounce_tasks[chat_id] = new_task
    logger.info(f"Userbot buffered message in chat {chat_id}. Waiting for silence...")


def register_userbot_handlers(client: Client):
    client.add_handler(MessageHandler(handle_incoming_private_message, filters.private), group=0)
    logger.info("Userbot handlers registered.")
