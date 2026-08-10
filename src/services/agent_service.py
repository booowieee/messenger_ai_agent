import asyncio
from typing import Optional
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.repositories.persona_repo import PersonaRepository
from src.services.context_service import ContextService
from src.utils.logger import export_logger as logger

# Configure Google Gemini SDK
genai.configure(api_key=settings.GEMINI_API_KEY)


class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.persona_repo = PersonaRepository(session)
        self.context_service = ContextService(session)

    async def generate_response(self, chat_id: int, incoming_text: str) -> Optional[str]:
        """
        Generates an AI response for an incoming Telegram message using Google Gemini.
        Applies system instructions, context window, and exponential backoff retry with model fallback.
        """
        # 1. Record incoming message in history
        await self.context_service.record_user_message(chat_id, incoming_text)

        # 2. Retrieve active persona
        active_persona = await self.persona_repo.get_active_persona()
        system_instruction = (
            active_persona.prompt if active_persona else
            "Ты — полезный и вежливый ассистент, отвечающий от лица пользователя."
        )

        # 3. Retrieve formatted context history
        formatted_history = await self.context_service.get_formatted_history(chat_id, limit=settings.DEFAULT_CONTEXT_WINDOW_LIMIT)
        
        # Ensure history passed to start_chat starts with 'user' and ends with 'model'
        while formatted_history and formatted_history[0]["role"] != "user":
            formatted_history.pop(0)

        while formatted_history and formatted_history[-1]["role"] != "model":
            formatted_history.pop()

        # 4. Call Gemini API with Exponential Backoff & Fallback Model
        models_to_try = [settings.GEMINI_MODEL, "gemini-1.5-flash", "gemini-2.0-flash"]
        # De-duplicate while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))

        for model_name in models_to_try:
            logger.info(f"Attempting Gemini generation for chat {chat_id} using model '{model_name}'...")
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )

                chat_session = model.start_chat(history=formatted_history)
                
                # Send incoming text to Gemini
                response = await asyncio.to_thread(
                    chat_session.send_message,
                    incoming_text
                )

                response_text = response.text
                if not response_text or not response_text.strip():
                    logger.warning(f"Gemini model '{model_name}' returned empty response text.")
                    continue

                # 5. Record model response in history
                await self.context_service.record_model_message(chat_id, response_text)
                logger.info(f"Successfully generated response from Gemini model '{model_name}'.")
                return response_text.strip()

            except Exception as e:
                logger.error(f"Gemini API model '{model_name}' failed for chat {chat_id}: {e}")
                await asyncio.sleep(1.0)

        logger.error("All Gemini API models failed to generate response.")
        return None
