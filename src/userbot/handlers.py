import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from src.database.connection import async_session_factory
from src.repositories.chat_repo import ChatRepository
from src.repositories.settings_repo import SettingsRepository
from src.services.agent_service import AgentService
from src.services.context_service import ContextService
from src.utils.human_delay import simulate_human_response_delay
from src.utils.logger import export_logger as logger

# Per-chat locks to prevent parallel processing of messages from the same user
_chat_locks: dict[int, asyncio.Lock] = {}


def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


def register_userbot_handlers(client: Client):

    @client.on_message(filters.private)
    async def handle_incoming_private_message(app: Client, message: Message):
        # 1. Ignore outgoing messages
        if message.outgoing or (message.from_user and message.from_user.is_self):
            return

        # 2. Ignore non-text or commands
        if not message.text or message.text.startswith("/"):
            return

        chat_id = message.chat.id
        user_text = message.text
        user_name = message.chat.first_name or message.chat.title or "User"

        logger.info(f"📩 USERBOT RECEIVED MESSAGE in chat {chat_id} ({user_name}): '{user_text}'")

        # 3. Check AI toggle and whitelist (separate DB session)
        async with async_session_factory() as session:
            settings_repo = SettingsRepository(session)
            chat_repo = ChatRepository(session)

            ai_enabled = await settings_repo.is_ai_enabled()
            if not ai_enabled:
                logger.info(f"⛔ Message from chat {chat_id} IGNORED: Global AI toggle is OFF.")
                return

            whitelist_only = await settings_repo.is_whitelist_only()
            if whitelist_only:
                is_whitelisted = await chat_repo.is_whitelisted(chat_id)
                if not is_whitelisted:
                    logger.info(f"⛔ Message from chat {chat_id} ({user_name}) IGNORED: NOT in Whitelist.")
                    return
            else:
                logger.info(f"🌐 Responding to chat {chat_id} in GLOBAL MODE.")

        # 4. Acquire per-chat lock to prevent parallel processing
        lock = _get_chat_lock(chat_id)
        async with lock:
            # 5. Generate AI response (separate DB session, released quickly)
            ai_response = None
            async with async_session_factory() as session:
                agent_service = AgentService(session)
                ai_response = await agent_service.generate_response(chat_id, user_text)

            if not ai_response:
                logger.warning(f"⚠️ No AI response generated for chat {chat_id}")
                return

            # 6. Send response to Telegram
            try:
                await simulate_human_response_delay(app, chat_id, text_length=len(ai_response))
                await app.send_message(chat_id, ai_response)
                logger.info(f"✅ USERBOT SENT AI RESPONSE to chat {chat_id}")

                # 7. Record model response ONLY after successful send (BUG-6 fix)
                async with async_session_factory() as session:
                    context_service = ContextService(session)
                    await context_service.record_model_message(chat_id, ai_response)

            except FloodWait as e:
                logger.warning(f"⚠️ FloodWait {e.value}s in chat {chat_id}. Response NOT saved to history.")
            except Exception as e:
                logger.exception(f"❌ Error sending to chat {chat_id}: {e}")
