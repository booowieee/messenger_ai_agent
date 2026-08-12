import os
from pyrogram import Client
from src.config import settings

os.makedirs("sessions", exist_ok=True)

_userbot_client: Client = None


def get_userbot_client() -> Client:
    """Gets or initializes the userbot client inside the active event loop."""
    global _userbot_client
    if _userbot_client is None:
        _userbot_client = Client(
            name=settings.USERBOT_SESSION_NAME,
            workdir="sessions",
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            device_model="Desktop",
            app_version="4.16.8 x64",
            system_version="Windows 10",
            lang_code="ru"
        )
    return _userbot_client
