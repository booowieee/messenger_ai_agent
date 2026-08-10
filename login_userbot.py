import os
from pyrogram import Client
from src.config import settings

os.makedirs("sessions", exist_ok=True)

print("==================================================")
print("     Telegram Userbot Interactive Login Helper    ")
print("==================================================")

app = Client(
    name=settings.USERBOT_SESSION_NAME,
    workdir="sessions",
    api_id=settings.TELEGRAM_API_ID,
    api_hash=settings.TELEGRAM_API_HASH,
)

with app:
    me = app.get_me()
    print("\n==================================================")
    print(f" ✅ AUTHORIZATION SUCCESSFUL!")
    print(f" User: {me.first_name} {me.last_name or ''} (@{me.username or me.id})")
    print(f" Saved session file: sessions/{settings.USERBOT_SESSION_NAME}.session")
    print("==================================================\n")
