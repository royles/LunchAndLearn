from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PublicConfig(BaseModel):
    llm_base_url: str
    llm_model: str
    supports_multimodal: bool = True
    supports_streaming: bool = True


class ConversationCreate(BaseModel):
    title: str = "New chat"


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "assistant", "system"]
    content: Any
    created_at: datetime

    model_config = {"from_attributes": True}


class ImageAttachment(BaseModel):
    """Base64 payload without the data URL prefix, plus MIME type."""

    mime_type: str = Field(default="image/png", pattern=r"^image/")
    data: str = Field(description="Base64-encoded image bytes")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32000)
    images: list[ImageAttachment] = Field(default_factory=list)
    model: str | None = None


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
