import os
from pyrogram import Client
from src.config import settings
from src.utils.logger import export_logger as logger

# Ensure sessions directory exists
os.makedirs("sessions", exist_ok=True)

userbot_client = Client(
    name=os.path.join("sessions", settings.USERBOT_SESSION_NAME),
    api_id=settings.TELEGRAM_API_ID,
    api_hash=settings.TELEGRAM_API_HASH,
)
