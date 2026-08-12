from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from src.config import settings
from src.database.connection import async_session_factory
from src.repositories.chat_repo import ChatRepository
from src.repositories.settings_repo import SettingsRepository
from src.userbot.client import get_userbot_client
from src.control_bot.keyboards.inline import get_whitelist_keyboard, get_back_keyboard
from src.utils.logger import export_logger as logger

router = Router()


class AddChatStates(StatesGroup):
    waiting_for_chat_id = State()


def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_TELEGRAM_ID


@router.callback_query(F.data == "menu_whitelist")
async def cb_menu_whitelist(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        settings_repo = SettingsRepository(session)
        active_chats = await chat_repo.list_active_chats()
        whitelist_only = await settings_repo.is_whitelist_only()

    mode_info = "🛡️ <b>Только Белый список</b> (ИИ отвечает только разрешенным диалогам)" if whitelist_only else "🌐 <b>Отвечать ВСЕМ</b> (ИИ отвечает во всех личных сообщениях)"

    text = (
        "📋 <b>Управление Режимом и Белым Списком</b>\n\n"
        f"Текущий режим: {mode_info}\n\n"
        "Вы можете переключить режим кнопкой ниже или добавить контакты."
    )
    await call.message.edit_text(text, reply_markup=get_whitelist_keyboard(active_chats, whitelist_only), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "toggle_mode")
async def cb_toggle_mode(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        chat_repo = ChatRepository(session)
        new_mode = await settings_repo.toggle_whitelist_only()
        active_chats = await chat_repo.list_active_chats()

    status_msg = "Режим: Только Белый Список 🛡️" if new_mode else "Режим: Отвечать ВСЕМ в ЛС 🌐"
    await call.answer(status_msg, show_alert=True)

    mode_info = "🛡️ <b>Только Белый список</b> (ИИ отвечает только разрешенным диалогам)" if new_mode else "🌐 <b>Отвечать ВСЕМ</b> (ИИ отвечает во всех личных сообщениях)"

    text = (
        "📋 <b>Управление Режимом и Белым Списком</b>\n\n"
        f"Текущий режим: {mode_info}\n\n"
        "Вы можете переключить режим кнопкой ниже или добавить контакты."
    )
    await call.message.edit_text(text, reply_markup=get_whitelist_keyboard(active_chats, new_mode), parse_mode="HTML")


@router.callback_query(F.data == "add_chat_prompt")
async def cb_add_chat_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(AddChatStates.waiting_for_chat_id)
    text = (
        "➕ <b>Добавление Чата в Белый Список</b>\n\n"
        "Отправьте <b>@username</b> (например: <code>@durov</code>), <b>числовой ID</b> (например: <code>123456789</code>) или перешлите любое сообщение из этого чата сюда.\n\n"
        "Напишите /cancel для отмены."
    )
    await call.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await call.answer()


@router.message(AddChatStates.waiting_for_chat_id)
async def process_add_chat(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление чата отменено.")
        return

    target_chat_id = None
    chat_title = "Личный диалог"
    username = None

    # 1. Forwarded message check
    if message.forward_from:
        target_chat_id = message.forward_from.id
        chat_title = message.forward_from.full_name or message.forward_from.first_name
        username = message.forward_from.username
    elif message.forward_from_chat:
        target_chat_id = message.forward_from_chat.id
        chat_title = message.forward_from_chat.title or message.forward_from_chat.username or "Канал/Чат"
        username = message.forward_from_chat.username

    # 2. Text input check (@username, t.me link or raw ID)
    elif message.text:
        raw_query = message.text.strip()
        if "t.me/" in raw_query:
            raw_query = "@" + raw_query.split("t.me/")[-1].strip("/")

        try:
            tg_chat = await get_userbot_client().get_chat(raw_query)
            target_chat_id = tg_chat.id
            chat_title = tg_chat.first_name or tg_chat.title or f"Чат {tg_chat.id}"
            if tg_chat.last_name:
                chat_title += f" {tg_chat.last_name}"
            username = tg_chat.username
            logger.info(f"Resolved MTProto chat for query '{raw_query}': ID={target_chat_id}, Title={chat_title}")
        except Exception as e:
            logger.warning(f"Could not resolve Telegram chat for '{raw_query}': {e}")
            if raw_query.lstrip('-').isdigit():
                target_chat_id = int(raw_query)
                chat_title = f"Чат {target_chat_id}"

    if not target_chat_id:
        await message.answer("⚠️ Не удалось распознать пользователь/чат. Попробуйте отправить <b>@username</b> или числовой ID.")
        return

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        chat = await chat_repo.add_to_whitelist(target_chat_id, chat_title, username)

    await state.clear()
    await message.answer(
        f"✅ Чат <b>{chat.chat_title}</b> (ID: <code>{chat.chat_id}</code>) успешно добавлен в белый список!",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("remove_chat_"))
async def cb_remove_chat(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    chat_id = int(call.data.split("remove_chat_")[1])

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        settings_repo = SettingsRepository(session)
        success = await chat_repo.remove_from_whitelist(chat_id)
        active_chats = await chat_repo.list_active_chats()
        whitelist_only = await settings_repo.is_whitelist_only()

    if success:
        await call.answer("✅ Чат удален из белого списка", show_alert=True)
    else:
        await call.answer("⚠️ Чат не найден", show_alert=True)

    await call.message.edit_reply_markup(reply_markup=get_whitelist_keyboard(active_chats, whitelist_only))
