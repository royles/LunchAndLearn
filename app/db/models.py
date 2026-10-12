from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelSettings(Base):
    """Singleton row (id=1) for OpenAI-compatible model connection settings."""

    __tablename__ = "model_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint_url: Mapped[str] = mapped_column(String(2048))
    model_id: Mapped[str] = mapped_column(String(256))
    token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class ChatAuditEntry(Base):
    """Append-only style audit of each user prompt and assistant response."""

    __tablename__ = "chat_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, index=True, nullable=True
    )
    user_message_id: Mapped[int] = mapped_column(Integer, index=True)
    assistant_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_text: Mapped[str] = mapped_column(Text)
    prompt_content_json: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    model_id: Mapped[str] = mapped_column(String(256))
    model_endpoint_url: Mapped[str] = mapped_column(String(2048))
    remote_user: Mapped[str | None] = mapped_column(String(512), nullable=True)
    remote_user_perm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    # JSON-serialized OpenAI-style content (string or multimodal part list)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
