from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import settings
from src.control_bot.handlers import admin, whitelist, persona
from src.utils.logger import export_logger as logger

control_bot = Bot(token=settings.CONTROL_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Register routers
dp.include_router(admin.router)
dp.include_router(whitelist.router)
dp.include_router(persona.router)


async def start_control_bot():
    logger.info("Starting Telegram Control Bot (Aiogram 3)...")
    await dp.start_polling(control_bot)
