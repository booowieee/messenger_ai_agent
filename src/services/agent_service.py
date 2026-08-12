import asyncio
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.repositories.persona_repo import PersonaRepository
from src.services.context_service import ContextService
from src.utils.logger import export_logger as logger

client = genai.Client(api_key=settings.GEMINI_API_KEY)
_models_logged = False


class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.persona_repo = PersonaRepository(session)
        self.context_service = ContextService(session)

    async def generate_response(self, chat_id: int, incoming_text: str) -> Optional[str]:
        global _models_logged
        if not _models_logged:
            try:
                # Список доступных моделей для диагностики квот и имен
                models = client.models.list()
                model_names = [m.name for m in models]
                logger.info(f"DEBUG: Available models for this API key: {model_names}")
                _models_logged = True
            except Exception as e:
                logger.error(f"Failed to query available models list: {e}")

        # Получаем историю до записи нового сообщения
        formatted_history = await self.context_service.get_formatted_history(chat_id, limit=settings.DEFAULT_CONTEXT_WINDOW_LIMIT)

        await self.context_service.record_user_message(chat_id, incoming_text)

        from src.repositories.settings_repo import SettingsRepository
        settings_repo = SettingsRepository(self.session)
        sys_settings = await settings_repo.get_settings()

        is_group = (chat_id < 0)
        if is_group:
            system_instruction = sys_settings.custom_group_prompt or sys_settings.custom_private_prompt
        else:
            system_instruction = sys_settings.custom_private_prompt

        if not system_instruction:
            system_instruction = "Ты — полезный и вежливый ассистент, отвечающий от лица владельца аккаунта. Отвечай естественно и кратко."

        # Добавляем инструкции по обработке медиа (фото и стикеры)
        media_instruction = (
            "\n\nИнструкции по обработке медиа:\n"
            "1. Если собеседник прислал тебе фото (ты увидишь [Фото] или [Фото: подпись] в диалоге), обязательно отвечай, что фото у тебя не грузится (например, плохой интернет, тупит связь, завис клиент и т.д.). Ни в коем случае не придумывай, что ты его видишь.\n"
            "2. Если собеседник прислал стикер (ты увидишь [Стикер: эмодзи] в диалоге), реагируй на эмодзи стикера.\n"
            "3. Ты можешь отвечать стикерами, вставляя в свой ответ тег [Стикер: эмодзи] (например: 'Привет! [Стикер: 👋]' или просто '[Стикер: 😊]'). Выбирай подходящие по смыслу эмодзи."
        )
        system_instruction += media_instruction

        contents = []
        for msg in formatted_history:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["parts"][0])]
            ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=incoming_text)]
        ))

        # Перебираем доступные модели в случае ошибок с квотами
        models_to_try = list(dict.fromkeys([
            settings.GEMINI_MODEL,
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash-lite",
            "gemini-pro-latest",
            "gemini-2.5-flash"
        ]))
        config = types.GenerateContentConfig(system_instruction=system_instruction)

        for model_name in models_to_try:
            logger.info(f"Attempting Gemini generation for chat {chat_id} using model '{model_name}'...")
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )

                response_text = response.text
                if not response_text or not response_text.strip():
                    logger.warning(f"Gemini model '{model_name}' returned empty response.")
                    continue

                logger.info(f"Successfully generated response from Gemini model '{model_name}'.")
                return response_text.strip()

            except Exception as e:
                logger.error(f"Gemini API model '{model_name}' failed for chat {chat_id}: {e}")
                await asyncio.sleep(1.0)

        logger.error("All Gemini API models failed to generate response.")
        return None
