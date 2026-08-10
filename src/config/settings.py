from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram MTProto (Userbot)
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    USERBOT_SESSION_NAME: str = "userbot_session"

    @field_validator("USERBOT_SESSION_NAME", mode="before")
    def validate_session_name(cls, v):
        if not v or not str(v).strip():
            return "userbot_session"
        return str(v).strip()

    # Telegram Bot API (Control Bot)
    CONTROL_BOT_TOKEN: str
    ADMIN_TELEGRAM_ID: int

    # Google Gemini API
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.6-flash"

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/messenger_ai"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Human Typing Simulation
    DEFAULT_HUMAN_DELAY_MIN: float = 2.0
    DEFAULT_HUMAN_DELAY_MAX: float = 6.0

    # AI Context Memory
    DEFAULT_CONTEXT_WINDOW_LIMIT: int = 15

    # System
    LOG_LEVEL: str = "INFO"


# Single unified configuration instance
settings = Settings()
