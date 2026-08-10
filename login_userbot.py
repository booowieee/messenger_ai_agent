import os
import sys
from pyrogram import Client
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    FloodWait,
)
from src.config import settings

os.makedirs("sessions", exist_ok=True)

print("\n==================================================")
print("     Telegram Userbot Explicit Login Script       ")
print("==================================================")
print(f"Loaded API_ID:   {settings.TELEGRAM_API_ID}")
print(f"Loaded API_HASH: {settings.TELEGRAM_API_HASH[:6]}... (masked)")
print(f"Session Name:    {settings.USERBOT_SESSION_NAME}")
print("==================================================\n")

app = Client(
    name=settings.USERBOT_SESSION_NAME,
    workdir="sessions",
    api_id=settings.TELEGRAM_API_ID,
    api_hash=settings.TELEGRAM_API_HASH,
)

async def login():
    await app.connect()
    try:
        # Check if already authorized
        me = await app.get_me()
        print(f"✅ Уже авторизован как: {me.first_name} (@{me.username or me.id})")
        await app.disconnect()
        return
    except Exception:
        pass

    phone = input("📱 Введите номер телефона в формате +79991234567: ").strip()
    if not phone.startswith("+"):
        print("⚠️ Ошибка: Номер должен начинаться с символа '+' (например: +79991234567)")
        await app.disconnect()
        return

    print(f"⏳ Отправляем запрос кода в Telegram для номера {phone}...")
    try:
        sent_code = await app.send_code(phone)
        print("\n" + "=" * 60)
        print(" 🔥 СЕРВЕР TELEGRAM ПОДТВЕРДИЛ ОТПРАВКУ КОДА!")
        print(" 📬 Проверьте чат 'Служебные уведомления' в Telegram на телефоне/ПК.")
        print("=" * 60 + "\n")
    except ApiIdInvalid:
        print("❌ ОШИБКА TELEGRAM: Неверный API_ID или API_HASH в вашем файле .env!")
        print("Перепроверьте данные с сайта https://my.telegram.org")
        await app.disconnect()
        return
    except PhoneNumberInvalid:
        print(f"❌ ОШИБКА TELEGRAM: Номер телефона '{phone}' не существует или введен неверно!")
        await app.disconnect()
        return
    except FloodWait as e:
        print(f"❌ ОШИБКА TELEGRAM: Превышен лимит попыток (FloodWait). Подождите {e.value} секунд перед повторной попыткой.")
        await app.disconnect()
        return
    except Exception as e:
        print(f"❌ ОШИБКА при отправке кода: {e}")
        await app.disconnect()
        return

    code = input("🔑 Введите 5-значный код из сообщения Telegram: ").strip()

    try:
        signed_in = await app.sign_in(phone, sent_code.phone_code_hash, code)
    except SessionPasswordNeeded:
        password = input("🔐 Включена 2FA. Введите ваш Облачный пароль Telegram: ").strip()
        signed_in = await app.check_password(password)
    except (PhoneCodeInvalid, PhoneCodeExpired) as e:
        print(f"❌ Ошибочный или истекший код: {e}")
        await app.disconnect()
        return

    print("\n==================================================")
    print(f" 🎉 УСПЕШНАЯ АВТОРИЗАЦИЯ!")
    print(f" Пользователь: {signed_in.first_name} (@{signed_in.username or signed_in.id})")
    print(f" Файл сессии сохранен в: sessions/{settings.USERBOT_SESSION_NAME}.session")
    print("==================================================\n")
    await app.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(login())
