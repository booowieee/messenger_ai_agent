import html
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from src.config import settings
from src.database.connection import async_session_factory
from src.repositories.persona_repo import PersonaRepository
from src.repositories.settings_repo import SettingsRepository
from src.control_bot.keyboards.inline import get_persona_keyboard, get_persona_mode_keyboard, get_back_keyboard

router = Router()


class EditPersonaStates(StatesGroup):
    waiting_for_prompt = State()


def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_TELEGRAM_ID


@router.callback_query(F.data == "menu_persona")
async def cb_menu_persona(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        persona_repo = PersonaRepository(session)
        
        active_private = await persona_repo.get_active_persona()
        active_group = await persona_repo.get_active_group_persona()
        
        private_name = active_private.name if active_private else "Не выбран"
        group_name = active_group.name if active_group else "Не выбран"

    text = (
        "<b>Настройка характера ответов (личности)</b>\n\n"
        "Вы можете задать разные личности ИИ для личной переписки и групповых чатов:\n\n"
        f"• <b>Личность для ЛС</b>: {private_name}\n"
        f"• <b>Личность для групп</b>: {group_name}\n\n"
        "Выберите раздел настройки:"
    )
    await call.message.edit_text(text, reply_markup=get_persona_mode_keyboard(private_name, group_name), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "menu_persona_private")
async def cb_menu_persona_private(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
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
        "<b>Личность для Личных Чатов (ЛС)</b>\n\n"
        f"<b>Активный пресет</b>: {active_persona.name if active_persona else 'Не выбран'}\n"
        f"<b>Текущий промпт</b>:\n<code>{escaped_prompt}</code>\n\n"
        "Выберите пресет ниже или измените его:"
    )
    await call.message.edit_text(text, reply_markup=get_persona_keyboard(personas, active_id, is_group=False), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "menu_persona_group")
async def cb_menu_persona_group(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    async with async_session_factory() as session:
        persona_repo = PersonaRepository(session)
        personas = await persona_repo.list_all()
        active_persona = await persona_repo.get_active_group_persona()
        active_id = active_persona.id if active_persona else 0

    prompt_text = active_persona.prompt if active_persona else ""
    if len(prompt_text) > 250:
        prompt_text = prompt_text[:250] + "..."
    escaped_prompt = html.escape(prompt_text)

    text = (
        "<b>Личность для Групповых Чатов</b>\n\n"
        f"<b>Активный пресет</b>: {active_persona.name if active_persona else 'Не выбран'}\n"
        f"<b>Текущий промпт</b>:\n<code>{escaped_prompt}</code>\n\n"
        "Выберите пресет ниже или измените его:"
    )
    await call.message.edit_text(text, reply_markup=get_persona_keyboard(personas, active_id, is_group=True), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("select_private_persona_"))
async def cb_select_private_persona(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    persona_id = int(call.data.split("select_private_persona_")[1])

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        persona_repo = PersonaRepository(session)
        
        await settings_repo.set_active_persona(persona_id)
        personas = await persona_repo.list_all()
        active_persona = await persona_repo.get_active_persona()

    await call.answer(f"ЛС: Выбрана личность {active_persona.name}", show_alert=True)

    prompt_text = active_persona.prompt if active_persona else ""
    if len(prompt_text) > 250:
        prompt_text = prompt_text[:250] + "..."
    escaped_prompt = html.escape(prompt_text)

    text = (
        "<b>Личность для Личных Чатов (ЛС)</b>\n\n"
        f"<b>Активный пресет</b>: {active_persona.name}\n"
        f"<b>Текущий промпт</b>:\n<code>{escaped_prompt}</code>\n\n"
        "Выберите пресет ниже или измените его:"
    )
    await call.message.edit_text(text, reply_markup=get_persona_keyboard(personas, persona_id, is_group=False), parse_mode="HTML")


@router.callback_query(F.data.startswith("select_group_persona_"))
async def cb_select_group_persona(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    persona_id = int(call.data.split("select_group_persona_")[1])

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        persona_repo = PersonaRepository(session)
        
        await settings_repo.set_active_group_persona(persona_id)
        personas = await persona_repo.list_all()
        active_persona = await persona_repo.get_active_group_persona()

    await call.answer(f"Группы: Выбрана личность {active_persona.name}", show_alert=True)

    prompt_text = active_persona.prompt if active_persona else ""
    if len(prompt_text) > 250:
        prompt_text = prompt_text[:250] + "..."
    escaped_prompt = html.escape(prompt_text)

    text = (
        "<b>Личность для Групповых Чатов</b>\n\n"
        f"<b>Активный пресет</b>: {active_persona.name}\n"
        f"<b>Текущий промпт</b>:\n<code>{escaped_prompt}</code>\n\n"
        "Выберите пресет ниже или измените его:"
    )
    await call.message.edit_text(text, reply_markup=get_persona_keyboard(personas, persona_id, is_group=True), parse_mode="HTML")


@router.callback_query(F.data == "edit_private_prompt")
async def cb_edit_private_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(EditPersonaStates.waiting_for_prompt)
    await state.update_data(edit_mode="private")
    text = (
        "<b>Изменение системного промпта (ЛС)</b>\n\n"
        "Отправьте новый текстовый промпт для автоответчика в ЛС.\n\n"
        "Для отмены отправьте /cancel."
    )
    await call.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "edit_group_prompt")
async def cb_edit_group_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(EditPersonaStates.waiting_for_prompt)
    await state.update_data(edit_mode="group")
    text = (
        "<b>Изменение системного промпта (Группы)</b>\n\n"
        "Отправьте новый текстовый промпт для автоответчика в группах.\n\n"
        "Для отмены отправьте /cancel."
    )
    await call.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await call.answer()


@router.message(EditPersonaStates.waiting_for_prompt)
async def process_new_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Изменение промпта отменено.")
        return

    new_prompt = message.text.strip()
    if len(new_prompt) < 5:
        await message.answer("Слишком короткий промпт. Напишите подробнее инструкцию.")
        return

    state_data = await state.get_data()
    edit_mode = state_data.get("edit_mode", "private")

    async with async_session_factory() as session:
        persona_repo = PersonaRepository(session)
        if edit_mode == "group":
            active_persona = await persona_repo.get_active_group_persona()
        else:
            active_persona = await persona_repo.get_active_persona()

        if active_persona:
            await persona_repo.update_persona_prompt(active_persona.id, new_prompt)

    await state.clear()
    await message.answer("Системный промпт успешно обновлен.", parse_mode="HTML")
