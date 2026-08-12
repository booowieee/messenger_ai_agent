from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.history_repo import HistoryRepository


class ContextService:
    def __init__(self, session: AsyncSession):
        self.history_repo = HistoryRepository(session)

    async def get_formatted_history(self, chat_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        # Подготовка истории сообщений для Gemini API с чередованием ролей
        history_records = await self.history_repo.get_recent_history(chat_id, limit)
        summary = await self.history_repo.get_summary(chat_id)

        formatted: List[Dict[str, Any]] = []

        if summary:
            formatted.append({
                "role": "user",
                "parts": [f"[Контекст прошлых диалогов: {summary}]"]
            })
            formatted.append({
                "role": "model",
                "parts": ["Понял, учитываю контекст предыдущего общения."]
            })

        for msg in history_records:
            role = "user" if msg.sender == "user" else "model"
            
            if not msg.text or not msg.text.strip():
                continue

            # Склеиваем сообщения от одного и того же автора подряд
            if formatted and formatted[-1]["role"] == role:
                formatted[-1]["parts"][0] += f"\n{msg.text}"
            else:
                formatted.append({
                    "role": role,
                    "parts": [msg.text]
                })

        return formatted

    async def record_user_message(self, chat_id: int, text: str):
        await self.history_repo.add_message(chat_id, sender="user", text=text)

    async def record_model_message(self, chat_id: int, text: str):
        await self.history_repo.add_message(chat_id, sender="model", text=text)
