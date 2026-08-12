# Telegram AI Userbot Agent

Ассистент на базе Google Gemini API для автоматических ответов в личном Telegram-аккаунте с админ-панелью через отдельного Telegram-бота (Control Bot).

## Основной функционал

* Включение и выключение автоответов через панель управления.
* Два режима работы: фильтрация по белому списку (whitelist) либо ответы во всех личных диалогах.
* Быстрое добавление собеседников в белый список по их юзернейму (`@username`), ссылке или Telegram ID.
* Настройка характера ответов (системного промпта) через выбор пресетов или ввод своего текста.
* Имитация набора текста (статус "печатает...") и регулируемая задержка перед отправкой.
* Сохранение контекста переписки в базе данных для поддержания связности диалога.

## Требования
* Python 3.10+ (при локальном запуске)
* Docker и Docker Compose (рекомендуется)
* API ключи Telegram (получить на my.telegram.org)
* Токен бота управления (создать через @BotFather)
* API ключ Google Gemini (получить в Google AI Studio)

## Настройка окружения
Создайте файл `.env` в корневой директории:
```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash_here
USERBOT_SESSION_NAME=userbot_session

CONTROL_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyZ
ADMIN_TELEGRAM_ID=987654321

GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
GEMINI_MODEL=gemini-2.5-flash

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/messenger_ai
REDIS_URL=redis://redis:6379/0
```

## Быстрый запуск (Docker)

1. Запустите контейнеры:
   ```bash
   docker compose up -d --build
   ```

2. Выполните первоначальную авторизацию юзербота (ввод номера телефона и кода авторизации):
   ```bash
   docker compose run --build --rm app python login_userbot.py
   ```

3. Перезапустите приложение в фоновом режиме:
   ```bash
   docker compose up -d --build
   ```

## Локальный запуск (без Docker)

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Запустите локальные сервисы PostgreSQL и Redis (порты по умолчанию).

3. Выполните авторизацию:
   ```bash
   python login_userbot.py
   ```

4. Запустите приложение:
   ```bash
   python main.py
   ```

## Панель управления

Откройте диалог с вашим Control Bot и отправьте команду `/start` или `/menu`:
* **Включение / Выключение** — глобальный тумблер работы ИИ.
* **Настройки режима и списка чатов** — управление белым списком и переключение на режим "отвечать всем".
* **Настройки личности** — изменение характера ответов.
* **Статус системы** — просмотр текущих параметров работы.
