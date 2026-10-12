from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ModelSettingsPublic(BaseModel):
    model_endpoint_url: str
    model_id: str
    model_token_masked: str | None = None
    has_model_token: bool = False
    supports_multimodal: bool = True
    supports_streaming: bool = True
    updated_at: datetime


class ModelSettingsUpdate(BaseModel):
    model_endpoint_url: str = Field(min_length=1, max_length=2048)
    model_id: str = Field(min_length=1, max_length=256)
    # Plaintext only on write; never returned by the API.
    model_token: str | None = Field(
        default=None,
        max_length=8192,
        description="New API token. Omit to keep existing. Empty string clears the token.",
    )


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


class ChatAuditEntryOut(BaseModel):
    id: int
    conversation_id: int | None
    user_message_id: int
    assistant_message_id: int | None
    prompt_text: str
    prompt_content: Any
    response_text: str | None
    image_count: int
    model_id: str
    model_endpoint_url: str
    remote_user: str | None
    remote_user_perm: str | None
    status: str
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
