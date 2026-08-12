from typing import AsyncGenerator
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, text

from src.config import settings
from src.database.models import Base, Persona, SystemSettings
from src.utils.logger import export_logger as logger

# Engine and Session Factory
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Redis client
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DEFAULT_PERSONAS = [
    {
        "name": "Дружелюбный (Обычный)",
        "prompt": "Ты — вежливый, позитивный и естественный помощник. Отвечаешь кратко и по делу от лица владельца аккаунта. Используешь живой разговорный язык, без канцелярита.",
        "is_default": True,
    },
    {
        "name": "Деловой (Профессиональный)",
        "prompt": "Ты — деловой представитель владельца аккаунта. Отвечаешь сдержанно, вежливо, профессионально. Фокусируешься на продуктивности и согласовании деталей.",
        "is_default": False,
    },
    {
        "name": "Ироничный / Саркастичный",
        "prompt": "Ты — остроумный и немного ироничный собеседник. Отвечаешь легко, с легким сарказмом и юмором, но остаешься дружелюбным.",
        "is_default": False,
    },
]


async def init_db():
    """Initializes tables and populates default settings/personas if missing."""
    logger.info("Initializing database schemas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Auto-migration for existing databases
        try:
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS whitelist_only BOOLEAN DEFAULT TRUE;"))
            await conn.execute(text("UPDATE system_settings SET whitelist_only = TRUE WHERE whitelist_only IS NULL;"))
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS active_group_persona_id INTEGER REFERENCES personas(id) ON DELETE SET NULL;"))
            await conn.execute(text("UPDATE system_settings SET active_group_persona_id = active_persona_id WHERE active_group_persona_id IS NULL;"))
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS custom_private_prompt TEXT;"))
            await conn.execute(text("ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS custom_group_prompt TEXT;"))
            
            # Копируем промпт из связанной активной личности, если кастомный промпт пуст
            await conn.execute(text("""
                UPDATE system_settings 
                SET custom_private_prompt = (SELECT prompt FROM personas WHERE id = system_settings.active_persona_id)
                WHERE custom_private_prompt IS NULL;
            """))
            await conn.execute(text("""
                UPDATE system_settings 
                SET custom_group_prompt = (SELECT prompt FROM personas WHERE id = system_settings.active_group_persona_id)
                WHERE custom_group_prompt IS NULL;
            """))
            # Если всё еще пусто (например, нет личности), пишем стандартный промпт
            default_prompt = "Ты — вежливый, позитивный и естественный помощник. Отвечаешь кратко и по делу от лица владельца аккаунта. Используешь живой разговорный язык, без канцелярита."
            await conn.execute(text(f"UPDATE system_settings SET custom_private_prompt = :prompt WHERE custom_private_prompt IS NULL;").bindparams(prompt=default_prompt))
            await conn.execute(text(f"UPDATE system_settings SET custom_group_prompt = :prompt WHERE custom_group_prompt IS NULL;").bindparams(prompt=default_prompt))
        except Exception as e:
            logger.warning(f"Database auto-migration notice: {e}")

    async with async_session_factory() as session:
        # Seed default personas
        result = await session.execute(select(Persona))
        existing_personas = result.scalars().all()
        
        default_persona_id = None
        if not existing_personas:
            logger.info("Seeding default personas into database...")
            for p_data in DEFAULT_PERSONAS:
                persona = Persona(**p_data)
                session.add(persona)
                await session.flush()
                if p_data["is_default"]:
                    default_persona_id = persona.id
            await session.commit()
        else:
            for p in existing_personas:
                if p.is_default:
                    default_persona_id = p.id
                    break

        # Seed initial system settings if not exists
        settings_result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
        system_settings = settings_result.scalar_one_or_none()
        
        if not system_settings:
            logger.info("Seeding initial SystemSettings into database...")
            default_prompt = "Ты — вежливый, позитивный и естественный помощник. Отвечаешь кратко и по делу от лица владельца аккаунта. Используешь живой разговорный язык, без канцелярита."
            if default_persona_id:
                res = await session.execute(select(Persona).where(Persona.id == default_persona_id))
                dp = res.scalar_one_or_none()
                if dp:
                    default_prompt = dp.prompt

            system_settings = SystemSettings(
                id=1,
                is_enabled=True,
                active_persona_id=default_persona_id,
                active_group_persona_id=default_persona_id,
                custom_private_prompt=default_prompt,
                custom_group_prompt=default_prompt,
                context_window_limit=settings.DEFAULT_CONTEXT_WINDOW_LIMIT,
                human_delay_min=settings.DEFAULT_HUMAN_DELAY_MIN,
                human_delay_max=settings.DEFAULT_HUMAN_DELAY_MAX
            )
            session.add(system_settings)
            await session.commit()

    logger.info("Database initialization completed.")
