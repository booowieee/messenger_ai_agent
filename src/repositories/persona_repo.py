from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Persona, SystemSettings
from src.utils.logger import export_logger as logger


class PersonaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> List[Persona]:
        result = await self.session.execute(select(Persona).order_by(Persona.id.asc()))
        return list(result.scalars().all())

    async def get_by_id(self, persona_id: int) -> Optional[Persona]:
        result = await self.session.execute(select(Persona).where(Persona.id == persona_id))
        return result.scalar_one_or_none()

    async def get_active_persona(self) -> Optional[Persona]:
        result = await self.session.execute(select(SystemSettings).where(SystemSettings.id == 1))
        settings_obj = result.scalar_one_or_none()
        if settings_obj and settings_obj.active_persona_id:
            return await self.get_by_id(settings_obj.active_persona_id)
        
        # Fallback to default persona
        default_result = await self.session.execute(select(Persona).where(Persona.is_default == True))
        return default_result.scalar_one_or_none()

    async def create_persona(self, name: str, prompt: str) -> Persona:
        persona = Persona(name=name, prompt=prompt, is_default=False)
        self.session.add(persona)
        await self.session.commit()
        await self.session.refresh(persona)
        logger.info(f"Created new persona: {name}")
        return persona

    async def update_persona_prompt(self, persona_id: int, prompt: str) -> Optional[Persona]:
        persona = await self.get_by_id(persona_id)
        if persona:
            persona.prompt = prompt
            await self.session.commit()
            await self.session.refresh(persona)
            logger.info(f"Updated prompt for persona ID {persona_id}")
            return persona
        return None
