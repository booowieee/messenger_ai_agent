from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.database.models import Persona, WhitelistChat


def get_main_menu_keyboard(is_enabled: bool) -> InlineKeyboardMarkup:
    toggle_text = "Автоответчик: Включен" if is_enabled else "Автоответчик: Выключен"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data="toggle_ai")],
            [InlineKeyboardButton(text="Настройки белого списка", callback_data="menu_whitelist")],
            [InlineKeyboardButton(text="Выбор личности (промпта)", callback_data="menu_persona")],
            [InlineKeyboardButton(text="Статус системы", callback_data="menu_status")],
        ]
    )
    return keyboard


def get_whitelist_keyboard(chats: list[WhitelistChat], whitelist_only: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    
    mode_text = "Режим: Только белый список" if whitelist_only else "Режим: Отвечать всем"
    buttons.append([InlineKeyboardButton(text=mode_text, callback_data="toggle_mode")])

    for chat in chats:
        title = chat.chat_title or f"Chat {chat.chat_id}"
        buttons.append([
            InlineKeyboardButton(text=title, callback_data=f"chat_info_{chat.chat_id}"),
            InlineKeyboardButton(text="Удалить", callback_data=f"remove_chat_{chat.chat_id}")
        ])

    buttons.append([InlineKeyboardButton(text="Добавить контакт", callback_data="add_chat_prompt")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_persona_mode_keyboard(active_private: str, active_group: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора режима настройки личности (ЛС или группы)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💬 Для ЛС: {active_private}", callback_data="menu_persona_private")],
            [InlineKeyboardButton(text=f"👥 Для групп: {active_group}", callback_data="menu_persona_group")],
            [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
        ]
    )


def get_persona_keyboard(personas: list[Persona], active_persona_id: int, is_group: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура со списком личностей для выбора в зависимости от типа чата (ЛС/группа)."""
    buttons = []
    prefix = "group" if is_group else "private"
    
    for p in personas:
        is_active = (p.id == active_persona_id)
        mark = "* " if is_active else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{mark}{p.name}",
                callback_data=f"select_{prefix}_persona_{p.id}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="Редактировать промпт", callback_data=f"edit_{prefix}_prompt")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="menu_persona")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="main_menu")]]
    )
