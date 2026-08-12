import asyncio
import random
import re
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.raw.functions.messages import GetStickers

from src.database.connection import async_session_factory
from src.repositories.chat_repo import ChatRepository
from src.repositories.settings_repo import SettingsRepository
from src.services.agent_service import AgentService
from src.services.context_service import ContextService
from src.utils.human_delay import simulate_human_response_delay
from src.utils.logger import export_logger as logger

# Блокировки, буферы и ID последних сообщений для реплай-ответов
_chat_locks: dict[int, asyncio.Lock] = {}
_pending_messages: dict[int, list[str]] = {}
_debounce_tasks: dict[int, asyncio.Task] = {}
_last_message_ids: dict[int, int] = {}


def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


async def get_sticker_by_emoji(client: Client, emoji: str):
    """Ищет подходящий стикер по эмодзи через официальное API Telegram."""
    try:
        # Извлекаем первый символ, если прислали строку из нескольких эмодзи
        emoji_char = emoji[0] if emoji else "😊"
        res = await client.invoke(GetStickers(emojis=emoji_char, hash=0))
        if res and hasattr(res, "stickers") and res.stickers:
            return random.choice(res.stickers)
    except Exception as e:
        logger.warning(f"Failed to fetch sticker for emoji '{emoji}': {e}")
    return None


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
                # Ищем [Стикер: emoji] в тексте ответа
                sticker_match = re.search(r"\[Стикер:\s*([^\]]+)\]", ai_response, re.IGNORECASE)
                
                sticker_doc = None
                clean_text = ai_response
                
                if sticker_match:
                    emoji = sticker_match.group(1).strip()
                    sticker_doc = await get_sticker_by_emoji(app, emoji)
                    if sticker_doc:
                        # Очищаем текст от тега стикера
                        clean_text = re.sub(r"\[Стикер:\s*[^\]]+\]", "", ai_response).strip()

                # 1. Если после очистки остался текст, отправляем его
                if clean_text:
                    await simulate_human_response_delay(app, chat_id, text_length=len(clean_text))
                    
                    is_group = (chat_id < 0)
                    reply_to_id = _last_message_ids.pop(chat_id, None) if is_group else None
                    await app.send_message(chat_id, clean_text, reply_to_message_id=reply_to_id)
                    logger.info(f"Userbot sent AI text response to chat {chat_id}")

                # 2. Если есть стикер, отправляем его с имитацией выбора стикера
                if sticker_doc:
                    try:
                        await app.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
                    except Exception:
                        pass
                    await asyncio.sleep(random.uniform(1.5, 3.0))
                    
                    is_group = (chat_id < 0)
                    # Если текст уже был отправлен, реплай на исходное сообщение вешать не нужно
                    reply_to_id = _last_message_ids.pop(chat_id, None) if (is_group and not clean_text) else None
                    await app.send_sticker(chat_id, sticker_doc, reply_to_message_id=reply_to_id)
                    logger.info(f"Userbot sent AI sticker response to chat {chat_id}")

                # Записываем полный сгенерированный ответ ИИ в историю
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

    # Извлекаем тип сообщения (текст, фото или стикер)
    user_text = ""
    if message.text:
        if message.text.startswith("/"):
            return
        user_text = message.text
    elif message.sticker:
        emoji = message.sticker.emoji or "😊"
        user_text = f"[Стикер: {emoji}]"
    elif message.photo:
        caption = f": {message.caption}" if message.caption else ""
        user_text = f"[Фото{caption}]"
    else:
        return

    chat_id = message.chat.id
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


async def handle_incoming_group_message(app: Client, message: Message):
    if message.outgoing or (message.from_user and message.from_user.is_self):
        return

    # Извлекаем тип сообщения (текст, фото или стикер)
    user_text = ""
    is_photo = False
    
    if message.text:
        if message.text.startswith("/"):
            return
        user_text = message.text
    elif message.sticker:
        emoji = message.sticker.emoji or "😊"
        user_text = f"[Стикер: {emoji}]"
    elif message.photo:
        caption = f": {message.caption}" if message.caption else ""
        user_text = f"[Фото{caption}]"
        is_photo = True
    else:
        return

    chat_id = message.chat.id
    user_name = message.from_user.first_name if message.from_user else "User"

    # Проверяем, обращено ли сообщение к нашему юзерботу:
    is_reply_to_me = False
    if message.reply_to_message:
        reply_to = message.reply_to_message
        if reply_to.from_user and reply_to.from_user.is_self:
            is_reply_to_me = True

    is_mentioned = False
    me = await app.get_me()
    
    mention_source = ""
    if message.text:
        mention_source = message.text
    elif is_photo and message.caption:
        mention_source = message.caption

    if me.username and f"@{me.username}" in mention_source:
        is_mentioned = True

    # Если это не ответ нам и не упоминание нашего юзернейма, просто игнорируем
    if not (is_reply_to_me or is_mentioned):
        return

    # Проверка глобальных настроек и белого списка для группы
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

    # Форматируем текст, чтобы ИИ понимал, кто именно говорит в группе
    formatted_text = f"{user_name}: {user_text}"

    # Добавляем в накопительный буфер чата
    if chat_id not in _pending_messages:
        _pending_messages[chat_id] = []
    _pending_messages[chat_id].append(formatted_text)
    
    # Сохраняем ID сообщения для реплая
    _last_message_ids[chat_id] = message.id

    # Перезапускаем таймер ожидания (debounce)
    old_task = _debounce_tasks.get(chat_id)
    if old_task and not old_task.done():
        old_task.cancel()

    new_task = asyncio.create_task(process_accumulated_messages_task(chat_id, app, message.chat.title or "Group"))
    _debounce_tasks[chat_id] = new_task
    logger.info(f"Userbot buffered group message in chat {chat_id}. Waiting for silence...")


def register_userbot_handlers(client: Client):
    client.add_handler(MessageHandler(handle_incoming_private_message, filters.private), group=0)
    client.add_handler(MessageHandler(handle_incoming_group_message, filters.group), group=0)
    logger.info("Userbot handlers registered.")
