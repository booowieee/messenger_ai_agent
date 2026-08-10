import os
from pyrogram import Client
from src.config import settings
from src.utils.logger import export_logger as logger

os.makedirs("sessions", exist_ok=True)

userbot_client = Client(
    name=settings.USERBOT_SESSION_NAME,
    workdir="sessions",
    api_id=settings.TELEGRAM_API_ID,
    api_hash=settings.TELEGRAM_API_HASH,
    device_model="Desktop",
    app_version="4.16.8 x64",
    system_version="Windows 10",
    lang_code="ru"
)
