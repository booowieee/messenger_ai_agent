import html
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from src.config import settings
from src.database.connection import async_session_factory
from src.repositories.settings_repo import SettingsRepository
from src.repositories.chat_repo import ChatRepository
from src.repositories.persona_repo import PersonaRepository
from src.control_bot.keyboards.inline import get_main_menu_keyboard, get_back_keyboard, get_persona_keyboard, get_whitelist_keyboard
from src.control_bot.keyboards.reply import get_admin_reply_keyboard
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
        logger.warning(f"Unauthorized access from user_id={message.from_user.id}")
        await message.reply(
            f"Доступ ограничен.\n\n"
            f"Ваш ID: <code>{message.from_user.id}</code>\n"
            f"Проверьте ADMIN_TELEGRAM_ID в файле .env и перезапустите контейнер.",
            parse_mode="HTML"
        )
        return

    # Сначала отправляем Reply-клавиатуру, чтобы она закрепилась в интерфейсе внизу
    await message.answer(
        "Клавиатура управления подключена. Вы можете использовать статичные кнопки внизу чата.",
        reply_markup=get_admin_reply_keyboard()
    )

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        is_enabled = await settings_repo.is_ai_enabled()

    text = (
        "<b>Панель управления автоответчиком</b>\n\n"
        "Здесь можно настроить автоответы для личного Telegram-аккаунта.\n\n"
        "• Включение / Выключение автоответов\n"
        "• Белый список чатов, в которых ИИ будет отвечать\n"
        "• Системный промпт (личность бота)"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(is_enabled), parse_mode="HTML")


@router.message(F.text == "👤 Настройка личности")
async def reply_menu_persona(message: Message):
    if not is_admin(message.from_user.id):
        return

    async with async_session_factory() as session:
        persona_repo = PersonaRepository(session)
        personas = await persona_repo.list_all()
        active_persona = await persona_repo.get_active_persona()
        active_id = active_persona.id if active_persona else 0

    prompt_text = active_persona.prompt if active_persona else ""
    if len(prompt_text) > 250:
        prompt_text = prompt_text[:250] + "..."
    escaped_prompt = html.escape(prompt_text)

    text = (
        "<b>Настройка характера ответов (личности)</b>\n\n"
        f"<b>Активный режим</b>: {active_persona.name if active_persona else 'Не выбран'}\n"
        f"<b>Промпт</b>:\n<code>{escaped_prompt}</code>\n\n"
        "Выберите пресет ниже или нажмите 'Изменить промпт', чтобы задать свои инструкции."
    )
    await message.answer(text, reply_markup=get_persona_keyboard(personas, active_id), parse_mode="HTML")


@router.message(F.text == "👥 Белый список")
async def reply_menu_whitelist(message: Message):
    if not is_admin(message.from_user.id):
        return

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        settings_repo = SettingsRepository(session)
        active_chats = await chat_repo.list_active_chats()
        whitelist_only = await settings_repo.is_whitelist_only()

    mode_info = "Только Белый список (ответы только выбранным контактам)" if whitelist_only else "Отвечать всем (ответы во всех личных диалогах)"

    text = (
        "<b>Настройка белого списка</b>\n\n"
        f"Текущий режим: {mode_info}\n\n"
        "Вы можете изменить режим работы или добавить новые контакты в список."
    )
    await message.answer(text, reply_markup=get_whitelist_keyboard(active_chats, whitelist_only), parse_mode="HTML")


@router.message(F.text == "⚙️ Статус и Управление")
async def reply_menu_status(message: Message):
    if not is_admin(message.from_user.id):
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        is_enabled = await settings_repo.is_ai_enabled()

    text = (
        "<b>Панель управления автоответчиком</b>\n\n"
        "Здесь можно настроить автоответы для личного Telegram-аккаунта.\n\n"
        "• Включение / Выключение автоответов\n"
        "• Белый список чатов, в которых ИИ будет отвечать\n"
        "• Системный промпт (личность бота)"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(is_enabled), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        is_enabled = await settings_repo.is_ai_enabled()

    text = (
        "<b>Главное меню</b>\n\n"
        "Выберите нужный раздел:"
    )
    await call.message.edit_text(text, reply_markup=get_main_menu_keyboard(is_enabled), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "toggle_ai")
async def cb_toggle_ai(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        new_state = await settings_repo.toggle_ai()

    state_text = "ВКЛЮЧЕН" if new_state else "ВЫКЛЮЧЕН"
    await call.answer(f"Автоответы: {state_text}", show_alert=True)

    await call.message.edit_reply_markup(reply_markup=get_main_menu_keyboard(new_state))


@router.callback_query(F.data == "menu_status")
async def cb_menu_status(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        chat_repo = ChatRepository(session)
        persona_repo = PersonaRepository(session)

        is_enabled = await settings_repo.is_ai_enabled()
        active_chats = await chat_repo.list_active_chats()
        active_persona = await persona_repo.get_active_persona()

    status_icon = "Включены" if is_enabled else "Выключены"
    persona_name = active_persona.name if active_persona else "Не выбрана"

    text = (
        "<b>Текущий статус системы</b>\n\n"
        f"• Автоответы: {status_icon}\n"
        f"• Личность: {persona_name}\n"
        f"• Белый список: {len(active_chats)} контактов\n"
        f"• Модель Gemini: <code>{settings.GEMINI_MODEL}</code>"
    )

    await call.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await call.answer()
