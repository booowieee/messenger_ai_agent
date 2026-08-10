import asyncio
import os
import signal
import sys
from pyrogram import idle

from src.config import settings
from src.database.connection import init_db, engine
from src.userbot.client import userbot_client
from src.userbot.handlers import register_userbot_handlers
from src.control_bot.bot import control_bot, dp
from src.utils.logger import export_logger as logger


async def main():
    logger.info("==================================================")
    logger.info("    Starting Telegram AI-Userbot Agent Application ")
    logger.info("==================================================")

    # 1. Initialize Database Schema & Seed Data
    try:
        await init_db()
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        sys.exit(1)

    # 2. Register Pyrogram Handlers
    register_userbot_handlers(userbot_client)

    # 3. Start Pyrogram Userbot Client
    session_file_path = os.path.join("sessions", f"{settings.USERBOT_SESSION_NAME}.session")
    if not os.path.exists(session_file_path):
        logger.critical(f"❌ ОШИБКА: Файл сессии юзербота '{session_file_path}' НЕ НАЙДЕН!")
        logger.critical("Сначала выполните однократную авторизацию командой: docker compose run --build --rm app python login_userbot.py")
        sys.exit(1)

    logger.info("Starting Pyrogram MTProto Userbot Client...")
    await userbot_client.start()
    me = await userbot_client.get_me()
    logger.info(f"Userbot started successfully as: {me.first_name} (@{me.username or me.id})")

    # 4. Start Control Bot polling and run concurrently
    logger.info("Starting Control Bot Polling...")
    polling_task = asyncio.create_task(dp.start_polling(control_bot))
    
    try:
        # Wait for shutdown signal via Pyrogram idle
        await idle()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received.")
    finally:
        logger.info("Stopping Control Bot Polling...")
        polling_task.cancel()
        logger.info("Stopping Pyrogram Userbot...")
        await userbot_client.stop()
        logger.info("Closing Database Engine...")
        await engine.dispose()
        logger.info("Application shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped manually.")
