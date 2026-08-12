from aiogram import Router
from aiogram.types import Message

from src.config import settings
from src.utils.logger import export_logger as logger

router = Router()


def is_admin(user_id: int) -> bool:
    try:
        return int(user_id) == int(settings.ADMIN_TELEGRAM_ID)
    except Exception:
        return False


@router.message()
async def fallback_any_message(message: Message):
    """Fallback handler — MUST be registered LAST so FSM handlers work."""
    logger.info(f"Control Bot fallback received message from user_id={message.from_user.id}: '{message.text}'")
    if is_admin(message.from_user.id):
        await message.reply(
            "ℹ️ Используйте /start или /menu для открытия панели управления.",
            parse_mode="HTML"
        )
    else:
        await message.reply(
            f"⛔ <b>Доступ запрещен.</b>\n\n"
            f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Укажите ваш ID в файле <code>.env</code> как ADMIN_TELEGRAM_ID и перезапустите контейнер.",
            parse_mode="HTML"
        )
