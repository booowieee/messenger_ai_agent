from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from src.config import settings
from src.database.connection import async_session_factory
from src.repositories.persona_repo import PersonaRepository
from src.repositories.settings_repo import SettingsRepository
from src.control_bot.keyboards.inline import get_persona_keyboard, get_back_keyboard

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
        personas = await persona_repo.list_all()
        active_persona = await persona_repo.get_active_persona()
        active_id = active_persona.id if active_persona else 0

    text = (
        "<b>Настройка характера ответов (личности)</b>\n\n"
        f"<b>Активный режим</b>: {active_persona.name if active_persona else 'Не выбран'}\n"
        f"<b>Промпт</b>:\n<code>{active_persona.prompt if active_persona else ''}</code>\n\n"
        "Выберите пресет ниже или нажмите 'Изменить промпт', чтобы задать свои инструкции."
    )
    await call.message.edit_text(text, reply_markup=get_persona_keyboard(personas, active_id), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("select_persona_"))
async def cb_select_persona(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    persona_id = int(call.data.split("select_persona_")[1])

    async with async_session_factory() as session:
        settings_repo = SettingsRepository(session)
        persona_repo = PersonaRepository(session)
        
        await settings_repo.set_active_persona(persona_id)
        
        personas = await persona_repo.list_all()
        active_persona = await persona_repo.get_active_persona()

    await call.answer(f"Выбрана личность: {active_persona.name}", show_alert=True)

    text = (
        "<b>Настройка характера ответов (личности)</b>\n\n"
        f"<b>Активный режим</b>: {active_persona.name}\n"
        f"<b>Промпт</b>:\n<code>{active_persona.prompt}</code>\n\n"
        "Выберите пресет ниже или нажмите 'Изменить промпт', чтобы задать свои инструкции."
    )
    await call.message.edit_text(text, reply_markup=get_persona_keyboard(personas, persona_id), parse_mode="HTML")


@router.callback_query(F.data == "edit_persona_prompt")
async def cb_edit_persona_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(EditPersonaStates.waiting_for_prompt)
    text = (
        "<b>Изменение системного промпта</b>\n\n"
        "Отправьте новый текстовый промпт (инструкцию) для автоответчика.\n"
        "Например: <i>«Отвечай кратко, дружелюбно, без использования официального тона.»</i>\n\n"
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

    async with async_session_factory() as session:
        persona_repo = PersonaRepository(session)
        active_persona = await persona_repo.get_active_persona()
        if active_persona:
            await persona_repo.update_persona_prompt(active_persona.id, new_prompt)

    await state.clear()
    await message.answer("Системный промпт успешно обновлен.", parse_mode="HTML")
