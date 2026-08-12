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
    logger.info(f"Control Bot fallback received message from user_id={message.from_user.id}: '{message.text}'")
    if is_admin(message.from_user.id):
        await message.reply(
            "Используйте команду /start или /menu для открытия настроек.",
            parse_mode="HTML"
        )
    else:
        await message.reply(
            f"Доступ ограничен.\n\n"
            f"Ваш ID: <code>{message.from_user.id}</code>\n"
            f"Проверьте настройки в .env и перезапустите контейнер.",
            parse_mode="HTML"
        )
