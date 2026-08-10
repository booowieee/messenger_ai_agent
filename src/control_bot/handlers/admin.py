from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from src.config import settings
from src.database.connection import async_session_factory
from src.repositories.settings_repo import SettingsRepository
from src.repositories.chat_repo import ChatRepository
from src.repositories.persona_repo import PersonaRepository
from src.control_bot.keyboards.inline import get_main_menu_keyboard, get_back_keyboard
from src.utils.logger import export_logger as logger

router = Router()


def is_admin(user_id: int) -> bool:
    try:
        return int(user_id) == int(settings.ADMIN_TELEGRAM_ID)
    except Exception:
        return False


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message):
    if not is_admin(message.from_user.id):
        logger.warning(f"Unauthorized access attempt in Control Bot from user_id={message.from_user.id} (Expected ADMIN_TELEGRAM_ID={settings.ADMIN_TELEGRAM_ID})")
        await message.reply(
            f"⛔ <b>Доступ запрещен.</b>\n\n"
            f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Указанный ADMIN_TELEGRAM_ID в .env: <code>{settings.ADMIN_TELEGRAM_ID}</code>\n\n"
            f"Укажите ваш правильный ID в файле <code>.env</code> и перезапустите контейнер.",
            parse_mode="HTML"
        )
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        is_enabled = await settings_repo.is_ai_enabled()

    text = (
        "🤖 <b>Панель Управления ИИ-Агентом</b>\n\n"
        "Здесь вы можете управлять состоянием работы ИИ-агента для вашего личного Telegram-аккаунта.\n\n"
        "• <b>Тумблер</b>: Включает или отключает автоответы.\n"
        "• <b>Белый список</b>: ИИ отвечает ТОЛЬКО в выбранных чатах.\n"
        "• <b>Личность (Persona)</b>: Промпт и стиль общения бота."
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(is_enabled), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        is_enabled = await settings_repo.is_ai_enabled()

    text = (
        "🤖 <b>Главное Меню Управления</b>\n\n"
        "Выберите раздел для настройки:"
    )
    await call.message.edit_text(text, reply_markup=get_main_menu_keyboard(is_enabled), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "toggle_ai")
async def cb_toggle_ai(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        new_state = await settings_repo.toggle_ai()

    state_text = "ВКЛЮЧЕН 🟢" if new_state else "ВЫКЛЮЧЕН 🔴"
    await call.answer(f"Состояние ИИ-агента: {state_text}", show_alert=True)

    await call.message.edit_reply_markup(reply_markup=get_main_menu_keyboard(new_state))


@router.callback_query(F.data == "menu_status")
async def cb_menu_status(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        chat_repo = ChatRepository(session)
        persona_repo = PersonaRepository(session)

        is_enabled = await settings_repo.is_ai_enabled()
        active_chats = await chat_repo.list_active_chats()
        active_persona = await persona_repo.get_active_persona()

    status_icon = "🟢 ВКЛЮЧЕН" if is_enabled else "🔴 ВЫКЛЮЧЕН"
    persona_name = active_persona.name if active_persona else "Не выбрав"

    text = (
        "ℹ️ <b>Текущий Статус Системы</b>\n\n"
        f"• <b>Статус ИИ-Агента</b>: {status_icon}\n"
        f"• <b>Активная Личность</b>: {persona_name}\n"
        f"• <b>Чатов в Белом списке</b>: {len(active_chats)}\n"
        f"• <b>Используемая модель</b>: <code>{settings.GEMINI_MODEL}</code>\n\n"
        "Система работает в штатном режиме."
    )

    await call.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await call.answer()


@router.message()
async def fallback_any_message(message: Message):
    """Fallback handler so Control Bot ALWAYS responds to any text/command."""
    logger.info(f"Control Bot received message from user_id={message.from_user.id}: '{message.text}'")
    if is_admin(message.from_user.id):
        await cmd_start(message)
    else:
        await message.reply(
            f"⛔ <b>Доступ запрещен.</b>\n\n"
            f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Указанный ADMIN_TELEGRAM_ID в .env: <code>{settings.ADMIN_TELEGRAM_ID}</code>\n\n"
            f"Измените ADMIN_TELEGRAM_ID в .env на ваш реальный ID ({message.from_user.id}) и перезапустите контейнер.",
            parse_mode="HTML"
        )
