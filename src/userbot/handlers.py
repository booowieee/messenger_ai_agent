from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from src.database.connection import async_session_factory
from src.services.agent_service import AgentService
from src.userbot.filters import ai_active_filter
from src.utils.human_delay import simulate_human_response_delay
from src.utils.logger import export_logger as logger


def register_userbot_handlers(client: Client):

    @client.on_message(filters.private & ai_active_filter)
    async def handle_incoming_private_message(app: Client, message: Message):
        chat_id = message.chat.id
        user_text = message.text

        logger.info(f"Userbot received message in chat {chat_id} ({message.chat.first_name}): '{user_text}'")

        try:
            async with async_session_factory() as session:
                agent_service = AgentService(session)
                ai_response = await agent_service.generate_response(chat_id, user_text)

            if not ai_response:
                logger.warning(f"No AI response generated for chat {chat_id}")
                return

            # Simulate human response delay & typing status
            await simulate_human_response_delay(app, chat_id, text_length=len(ai_response))

            # Send reply message
            await app.send_message(chat_id, ai_response)
            logger.info(f"Userbot sent AI response to chat {chat_id}")

        except FloodWait as e:
            logger.warning(f"Telegram FloodWait hit for {e.value} seconds in chat {chat_id}")
        except Exception as e:
            logger.exception(f"Unexpected error in Userbot handler for chat {chat_id}: {e}")
