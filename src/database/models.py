from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    active_persona_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )
    context_window_limit: Mapped[int] = mapped_column(Integer, default=15)
    human_delay_min: Mapped[float] = mapped_column(Float, default=2.0)
    human_delay_max: Mapped[float] = mapped_column(Float, default=6.0)

    active_persona: Mapped[Optional["Persona"]] = relationship("Persona", lazy="selectin")


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WhitelistChat(Base):
    __tablename__ = "whitelist_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    chat_title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MessageHistory(Base):
    __tablename__ = "message_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(16), nullable=False)  # 'user' or 'model'
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ChatSummary(Base):
    __tablename__ = "chat_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
