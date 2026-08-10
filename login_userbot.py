import os
import sys
from pyrogram import Client
from pyrogram.enums import SentCodeType
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
print("     Telegram Userbot Diagnostic Login Script     ")
print("==================================================")
print(f"Loaded API_ID:   {settings.TELEGRAM_API_ID}")
print(f"Loaded API_HASH: {settings.TELEGRAM_API_HASH[:6]}... (masked)")
print("==================================================\n")

app = Client(
    name=settings.USERBOT_SESSION_NAME,
    workdir="sessions",
    api_id=settings.TELEGRAM_API_ID,
    api_hash=settings.TELEGRAM_API_HASH,
)

def describe_code_type(code_type: SentCodeType) -> str:
    if code_type == SentCodeType.APP:
        return "📱 ЧАТ ВНУТРИ ПРИЛОЖЕНИЯ TELEGRAM (Чат 'Служебные уведомления' / 'Telegram Notifications')"
    elif code_type == SentCodeType.SMS:
        return "📩 СМС-СООБЩЕНИЕ на ваш мобильный номер"
    elif code_type == SentCodeType.CALL:
        return "📞 ВХОДЯЩИЙ ЗВОНОК (диктор продиктует код по телефону)"
    elif code_type == SentCodeType.FLASH_CALL:
        return "📞 ЗВОНОК-СБРОС (FLASH CALL) - кодом являются последние цифры номера звонящего!"
    elif code_type == SentCodeType.EMAIL_CODE:
        return "📧 ЭЛЕКТРОННАЯ ПОЧТА, привязанная к аккаунту"
    return str(code_type)

async def login():
    await app.connect()
    try:
        me = await app.get_me()
        print(f"✅ УЖЕ АВТОРИЗОВАН как: {me.first_name} (@{me.username or me.id})")
        await app.disconnect()
        return
    except Exception:
        pass

    phone = input("📱 Введите номер телефона (+79991234567): ").strip()
    if not phone.startswith("+"):
        print("⚠️ Ошибка: Номер должен начинаться с '+'")
        await app.disconnect()
        return

    print(f"\n⏳ Запрос кода в Telegram для номера {phone}...")
    try:
        sent_code = await app.send_code(phone)
        delivery_method = describe_code_type(sent_code.type)
        
        print("\n" + "░" * 60)
        print(f" 🎯 TELEGRAM ВЫБРАЛ СПОСОБ ДОСТАВКИ:")
        print(f" -> {delivery_method}")
        print("░" * 60 + "\n")
    except ApiIdInvalid:
        print("❌ ОШИБКА: Неверный API_ID или API_HASH в .env!")
        await app.disconnect()
        return
    except PhoneNumberInvalid:
        print("❌ ОШИБКА: Неверный номер телефона!")
        await app.disconnect()
        return
    except FloodWait as e:
        print(f"❌ ОШИБКА: Лимит запросов. Подождите {e.value} секунд.")
        await app.disconnect()
        return
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        await app.disconnect()
        return

    print("Подсказка: Если код не приходит, введите 'r' для повторного запроса через SMS/Звонок.")
    user_input = input("🔑 Введите 5-значный код (или 'r' для повтора): ").strip()

    if user_input.lower() == 'r':
        print("\n⏳ Повторный запрос кода через альтернативный способ...")
        try:
            sent_code = await app.resend_code(phone, sent_code.phone_code_hash)
            delivery_method = describe_code_type(sent_code.type)
            print(f"🎯 Альтернативный способ: {delivery_method}")
            user_input = input("🔑 Введите 5-значный код: ").strip()
        except Exception as e:
            print(f"❌ Ошибка повторного запроса: {e}")
            await app.disconnect()
            return

    try:
        signed_in = await app.sign_in(phone, sent_code.phone_code_hash, user_input)
    except SessionPasswordNeeded:
        password = input("🔐 Введите 2FA Облачный пароль Telegram: ").strip()
        signed_in = await app.check_password(password)
    except (PhoneCodeInvalid, PhoneCodeExpired) as e:
        print(f"❌ Неверный или истекший код: {e}")
        await app.disconnect()
        return

    print("\n" + "=" * 50)
    print(f" 🎉 УСПЕШНЫЙ ВХОД! Учетная запись: {signed_in.first_name}")
    print(f" Файл сессии создан в: sessions/{settings.USERBOT_SESSION_NAME}.session")
    print("=" * 50 + "\n")
    await app.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(login())
