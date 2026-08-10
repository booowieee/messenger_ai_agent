from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from src.database.connection import async_session_factory
from src.repositories.chat_repo import ChatRepository
from src.repositories.settings_repo import SettingsRepository
from src.services.agent_service import AgentService
from src.utils.human_delay import simulate_human_response_delay
from src.utils.logger import export_logger as logger


def register_userbot_handlers(client: Client):

    @client.on_message(filters.private)
    async def handle_incoming_private_message(app: Client, message: Message):
        # 1. Ignore outgoing messages (sent by self from phone/desktop)
        if message.outgoing or (message.from_user and message.from_user.is_self):
            return

        # 2. Ignore non-text or commands
        if not message.text or message.text.startswith("/"):
            return

        chat_id = message.chat.id
        user_text = message.text
        user_name = message.chat.first_name or message.chat.title or "User"

        logger.info(f"📩 USERBOT RECEIVED MESSAGE in chat {chat_id} ({user_name}): '{user_text}'")

        async with async_session_factory() as session:
            settings_repo = SettingsRepository(session)
            chat_repo = ChatRepository(session)

            # 3. Check Global AI Toggle
            ai_enabled = await settings_repo.is_ai_enabled()
            if not ai_enabled:
                logger.info(f"⛔ Message from chat {chat_id} IGNORED: Global AI toggle is OFF in Control Bot.")
                return

            # 4. Check Whitelist Mode
            whitelist_only = await settings_repo.is_whitelist_only()
            if whitelist_only:
                is_whitelisted = await chat_repo.is_whitelisted(chat_id)
                if not is_whitelisted:
                    logger.info(f"⛔ Message from chat {chat_id} ({user_name}) IGNORED: Chat ID {chat_id} is NOT in Whitelist. (Tip: You can switch to Global Mode in Control Bot!).")
                    return
            else:
                logger.info(f"🌐 Responding to chat {chat_id} in GLOBAL MODE (Whitelist filter bypassed).")

            # 5. Generate AI Response
            logger.info(f"🤖 Generating AI response for chat {chat_id}...")
            agent_service = AgentService(session)
            ai_response = await agent_service.generate_response(chat_id, user_text)

        if not ai_response:
            logger.warning(f"⚠️ No AI response generated for chat {chat_id}")
            return

        try:
            # 6. Simulate human response delay & typing status
            await simulate_human_response_delay(app, chat_id, text_length=len(ai_response))

            # 7. Send reply message
            await app.send_message(chat_id, ai_response)
            logger.info(f"✅ USERBOT SENT AI RESPONSE to chat {chat_id}: '{ai_response}'")

        except FloodWait as e:
            logger.warning(f"⚠️ Telegram FloodWait hit for {e.value} seconds in chat {chat_id}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error sending message to chat {chat_id}: {e}")
