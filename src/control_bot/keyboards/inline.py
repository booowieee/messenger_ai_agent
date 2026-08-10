from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.database.models import Persona, WhitelistChat


def get_main_menu_keyboard(is_enabled: bool) -> InlineKeyboardMarkup:
    toggle_text = "🟢 Агент: ВКЛЮЧЕН" if is_enabled else "🔴 Агент: ВЫКЛЮЧЕН"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data="toggle_ai")],
            [InlineKeyboardButton(text="📋 Белый список чатов", callback_data="menu_whitelist")],
            [InlineKeyboardButton(text="🎭 Настройки Личности (Persona)", callback_data="menu_persona")],
            [InlineKeyboardButton(text="ℹ️ Статус системы", callback_data="menu_status")],
        ]
    )
    return keyboard


def get_whitelist_keyboard(chats: list[WhitelistChat]) -> InlineKeyboardMarkup:
    buttons = []
    for chat in chats:
        title = chat.chat_title or f"Chat {chat.chat_id}"
        buttons.append([
            InlineKeyboardButton(text=f"💬 {title}", callback_data=f"chat_info_{chat.chat_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"remove_chat_{chat.chat_id}")
        ])

    buttons.append([InlineKeyboardButton(text="➕ Добавить чат по ID", callback_data="add_chat_prompt")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад в Главное Меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_persona_keyboard(personas: list[Persona], active_persona_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for p in personas:
        is_active = (p.id == active_persona_id)
        mark = "✅ " if is_active else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{mark}{p.name}",
                callback_data=f"select_persona_{p.id}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="✏️ Изменить промпт активной личности", callback_data="edit_persona_prompt")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад в Главное Меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]]
    )
