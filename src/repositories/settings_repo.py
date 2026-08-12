from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import SystemSettings
from src.database.connection import redis_client
from src.utils.logger import export_logger as logger

REDIS_TOGGLE_KEY = "system:ai_enabled"
REDIS_WHITELIST_ONLY_KEY = "system:whitelist_only"


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_settings(self) -> SystemSettings:
        result = await self.session.execute(select(SystemSettings).where(SystemSettings.id == 1))
        settings_obj = result.scalar_one_or_none()
        if not settings_obj:
            settings_obj = SystemSettings(id=1, is_enabled=True, whitelist_only=True)
            self.session.add(settings_obj)
            await self.session.commit()
            await self.session.refresh(settings_obj)
        return settings_obj

    async def is_ai_enabled(self) -> bool:
        cached_val = await redis_client.get(REDIS_TOGGLE_KEY)
        if cached_val is not None:
            return cached_val == "1"
        
        sys_settings = await self.get_settings()
        enabled = sys_settings.is_enabled
        await redis_client.set(REDIS_TOGGLE_KEY, "1" if enabled else "0")
        return enabled

    async def toggle_ai(self) -> bool:
        sys_settings = await self.get_settings()
        new_state = not sys_settings.is_enabled
        sys_settings.is_enabled = new_state
        await self.session.commit()
        
        await redis_client.set(REDIS_TOGGLE_KEY, "1" if new_state else "0")
        logger.info(f"Global AI Toggle changed to: {new_state}")
        return new_state

    async def is_whitelist_only(self) -> bool:
        cached_val = await redis_client.get(REDIS_WHITELIST_ONLY_KEY)
        if cached_val is not None:
            return cached_val == "1"

        sys_settings = await self.get_settings()
        whitelist_only = getattr(sys_settings, "whitelist_only", True)
        if whitelist_only is None:
            whitelist_only = True
        await redis_client.set(REDIS_WHITELIST_ONLY_KEY, "1" if whitelist_only else "0")
        return whitelist_only

    async def toggle_whitelist_only(self) -> bool:
        sys_settings = await self.get_settings()
        current = getattr(sys_settings, "whitelist_only", True)
        if current is None:
            current = True
        new_state = not current
        sys_settings.whitelist_only = new_state
        await self.session.commit()
        
        await redis_client.set(REDIS_WHITELIST_ONLY_KEY, "1" if new_state else "0")
        logger.info(f"Whitelist-Only Mode changed to: {new_state}")
        return new_state

    async def set_active_persona(self, persona_id: int) -> SystemSettings:
        sys_settings = await self.get_settings()
        sys_settings.active_persona_id = persona_id
        await self.session.commit()
        await self.session.refresh(sys_settings)
        return sys_settings

    async def set_active_group_persona(self, persona_id: int) -> SystemSettings:
        sys_settings = await self.get_settings()
        sys_settings.active_group_persona_id = persona_id
        await self.session.commit()
        await self.session.refresh(sys_settings)
        return sys_settings
