import asyncio
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
    logger.info("Starting Pyrogram MTProto Userbot Client...")
    await userbot_client.start()
    me = await userbot_client.get_me()
    logger.info(f"Userbot started successfully as: {me.first_name} (@{me.username or me.id})")

    # 4. Start Control Bot polling and run concurrently
    logger.info("Starting Control Bot Polling...")
    
    try:
        # Run Aiogram polling and keep Pyrogram idle concurrently
        await asyncio.gather(
            dp.start_polling(control_bot),
            idle()
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received.")
    finally:
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
