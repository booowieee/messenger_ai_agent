import asyncio
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.repositories.persona_repo import PersonaRepository
from src.services.context_service import ContextService
from src.utils.logger import export_logger as logger

# Initialize Google Genai client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.persona_repo = PersonaRepository(session)
        self.context_service = ContextService(session)

    async def generate_response(self, chat_id: int, incoming_text: str) -> Optional[str]:
        # 1. Retrieve formatted context history FIRST (before recording)
        formatted_history = await self.context_service.get_formatted_history(chat_id, limit=settings.DEFAULT_CONTEXT_WINDOW_LIMIT)

        # 2. Record incoming message in history
        await self.context_service.record_user_message(chat_id, incoming_text)

        # 3. Retrieve active persona for system instruction
        active_persona = await self.persona_repo.get_active_persona()
        system_instruction = (
            active_persona.prompt if active_persona else
            "Ты — полезный и вежливый ассистент, отвечающий от лица владельца аккаунта. Отвечай естественно и кратко."
        )

        # 4. Build contents: history + current message
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

        # 5. Cascade model fallback with native async
        models_to_try = list(dict.fromkeys([settings.GEMINI_MODEL, "gemini-2.5-flash", "gemini-2.0-flash"]))

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
        )

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
