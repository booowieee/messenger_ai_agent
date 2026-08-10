from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from src.config import settings
from src.database.connection import async_session_factory
from src.repositories.chat_repo import ChatRepository
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
        active_chats = await chat_repo.list_active_chats()

    text = (
        "📋 <b>Управление Белым Списком (Whitelist)</b>\n\n"
        "ИИ-агент отвечает только в разрешенных ниже диалогах.\n"
        "Нажмите на чат, чтобы просмотреть информацию, или на кнопку 'Удалить'."
    )
    await call.message.edit_text(text, reply_markup=get_whitelist_keyboard(active_chats), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "add_chat_prompt")
async def cb_add_chat_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(AddChatStates.waiting_for_chat_id)
    text = (
        "➕ <b>Добавление Чата в Белый Список</b>\n\n"
        "Отправьте <b>числовой ID чата</b> (например: <code>123456789</code>) или перешлите любое сообщение из этого чата сюда.\n\n"
        "<i>Подсказка: Узнать ID любого собеседника можно, посмотрев логи сервера <code>docker compose logs app</code> при входящем сообщении.</i>\n\n"
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

    # Check if forwarded message
    if message.forward_from_chat:
        target_chat_id = message.forward_from_chat.id
        chat_title = message.forward_from_chat.title or message.forward_from_chat.username or "Канал/Чат"
        username = message.forward_from_chat.username
    elif message.forward_from:
        target_chat_id = message.forward_from.id
        chat_title = message.forward_from.full_name
        username = message.forward_from.username
    elif message.text and (message.text.lstrip('-').isdigit()):
        target_chat_id = int(message.text.strip())
        chat_title = f"Чат {target_chat_id}"

    if not target_chat_id:
        await message.answer("⚠️ Не удалось распознать ID чата. Пожалуйста, введите корректный числовой ID или перешлите сообщение.")
        return

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        chat = await chat_repo.add_to_whitelist(target_chat_id, chat_title, username)

    await state.clear()
    await message.answer(f"✅ Чат <b>{chat.chat_title}</b> (<code>{chat.chat_id}</code>) успешно добавлен в белый список!", parse_mode="HTML")


@router.callback_query(F.data.startswith("remove_chat_"))
async def cb_remove_chat(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    chat_id = int(call.data.split("remove_chat_")[1])

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        success = await chat_repo.remove_from_whitelist(chat_id)
        active_chats = await chat_repo.list_active_chats()

    if success:
        await call.answer("✅ Чат удален из белого списка", show_alert=True)
    else:
        await call.answer("⚠️ Чат не найден", show_alert=True)

    await call.message.edit_reply_markup(reply_markup=get_whitelist_keyboard(active_chats))
