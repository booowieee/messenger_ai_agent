from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import settings
from src.control_bot.handlers import admin, whitelist, persona, fallback

_control_bot: Bot = None
_dp: Dispatcher = None


def get_control_bot() -> tuple[Bot, Dispatcher]:
    """Gets or initializes the control bot and dispatcher inside the active event loop."""
    global _control_bot, _dp
    if _control_bot is None:
        _control_bot = Bot(token=settings.CONTROL_BOT_TOKEN)
        _dp = Dispatcher(storage=MemoryStorage())

        # Register routers — ORDER MATTERS! Fallback MUST be last.
        _dp.include_router(admin.router)
        _dp.include_router(whitelist.router)
        _dp.include_router(persona.router)
        _dp.include_router(fallback.router)  # LAST — catches unhandled messages
        
    return _control_bot, _dp
