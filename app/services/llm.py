import json
from collections.abc import AsyncIterator, Iterable
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.schemas import ImageAttachment
from app.services.model_settings import ResolvedModelConfig


def build_user_content(text: str, images: Iterable[ImageAttachment]) -> str | list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for img in images:
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{img.mime_type};base64,{img.data}"},
            }
        )
    if len(parts) == 1:
        return text
    return parts


def parse_stored_content(raw: str) -> str | list[Any]:
    try:
        parsed = json.loads(raw)
        return parsed
    except json.JSONDecodeError:
        return raw


def serialize_content(content: str | list[Any]) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content)


def to_openai_messages(
    history: list[tuple[str, str | list[Any]]],
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for role, content in history:
        messages.append({"role": role, "content": content})
    return messages


def get_client(resolved: ResolvedModelConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=resolved.endpoint_url,
        api_key=resolved.api_token or "not-needed",
    )


async def stream_chat_completion(
    messages: list[dict[str, Any]],
    resolved: ResolvedModelConfig,
    model_override: str | None = None,
) -> AsyncIterator[str]:
    client = get_client(resolved)
    chosen = model_override or resolved.model_id
    stream = await client.chat.completions.create(
        model=chosen,
        messages=messages,
        stream=True,
        max_tokens=settings.llm_max_tokens,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
