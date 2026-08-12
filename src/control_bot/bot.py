from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import settings
from src.control_bot.handlers import admin, whitelist, persona, fallback
from src.utils.logger import export_logger as logger

control_bot = Bot(token=settings.CONTROL_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Register routers — ORDER MATTERS! Fallback MUST be last.
dp.include_router(admin.router)
dp.include_router(whitelist.router)
dp.include_router(persona.router)
dp.include_router(fallback.router)  # LAST — catches unhandled messages
