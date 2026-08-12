from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает статичную клавиатуру управления внизу чата для админа."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Настройка личности"),
                KeyboardButton(text="👥 Белый список")
            ],
            [
                KeyboardButton(text="🖼️ Стикеры"),
                KeyboardButton(text="⚙️ Статус и Управление")
            ]
        ],
        resize_keyboard=True,
        persistent=True
    )
