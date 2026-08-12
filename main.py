import asyncio
import os
import sys
import signal

from src.config import settings
from src.database.connection import init_db, engine
from src.userbot.client import get_userbot_client
from src.userbot.handlers import register_userbot_handlers
from src.control_bot.bot import get_control_bot
from src.utils.logger import export_logger as logger

# Global event to control graceful shutdown
shutdown_event = asyncio.Event()


def handle_polling_exception(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.critical(f"❌ Control Bot Polling crashed with error: {e}")


async def userbot_heartbeat_loop():
    """Periodically queries userbot client status to ensure MTProto update connection is alive."""
    await asyncio.sleep(15)  # Wait for startup
    userbot_client = get_userbot_client()
    while True:
        try:
            me = await userbot_client.get_me()
            logger.info(f"💓 [HEARTBEAT] Userbot MTProto client connection is active: @{me.username or me.id}")
        except Exception as e:
            logger.error(f"💔 [HEARTBEAT ERROR] Userbot connection lost or unresponsive: {e}")
        await asyncio.sleep(30)


def setup_signal_handlers():
    """Setup OS signal handlers for graceful shutdown without relying on pyrogram.idle()"""
    loop = asyncio.get_running_loop()
    
    def shutdown_handler():
        logger.info("Received termination signal. Triggering graceful shutdown...")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_handler)
        except NotImplementedError:
            # On Windows signal handlers are not fully supported in asyncio loops sometimes
            pass


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

    # Instantiate lazy client & bot/dispatcher inside the active event loop
    userbot_client = get_userbot_client()
    control_bot, dp = get_control_bot()

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

    # Start userbot heartbeat task
    heartbeat_task = asyncio.create_task(userbot_heartbeat_loop())

    # 4. Clear Webhook & Start Control Bot Polling
    logger.info("Clearing old webhooks for Control Bot...")
    try:
        await control_bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")

    logger.info("Starting Control Bot Polling...")
    polling_task = asyncio.create_task(dp.start_polling(control_bot))
    polling_task.add_done_callback(handle_polling_exception)

    # Setup termination signal handlers
    setup_signal_handlers()
    
    try:
        # Wait until shutdown event is set (either by OS signal or program logic)
        await shutdown_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown initiated by keyboard/system interrupt.")
    finally:
        logger.info("Stopping Control Bot Polling...")
        polling_task.cancel()
        logger.info("Stopping Heartbeat...")
        heartbeat_task.cancel()
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
