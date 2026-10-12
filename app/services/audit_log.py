"""Comprehensive audit trail for prompt/response pairs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ChatAuditEntry
from app.services.llm import parse_stored_content, serialize_content


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _audit_dir() -> Path:
    path = settings.project_root / "data" / "audit"
    path.mkdir(parents=True, exist_ok=True)
    return path


def audit_jsonl_path() -> Path:
    custom = settings.audit_jsonl_path
    if custom:
        custom.parent.mkdir(parents=True, exist_ok=True)
        return custom.resolve()
    return (_audit_dir() / "chat_audit.jsonl").resolve()


def extract_prompt_text(content: str | list[Any]) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    image_count = 0
    for part in content:
        if isinstance(part, dict):
            if part.get("type") == "text" and part.get("text"):
                parts.append(str(part["text"]))
            elif part.get("type") == "image_url":
                image_count += 1
    text = "\n".join(parts).strip()
    if image_count:
        suffix = f" [{image_count} image(s) attached]"
        text = f"{text}{suffix}" if text else suffix.strip()
    return text or ""


def count_images(content: str | list[Any]) -> int:
    if isinstance(content, str):
        return 0
    return sum(1 for p in content if isinstance(p, dict) and p.get("type") == "image_url")


def append_jsonl(record: dict[str, Any]) -> None:
    line = json.dumps(record, default=str, ensure_ascii=False)
    path = audit_jsonl_path()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def record_exchange_started(
    db: Session,
    *,
    conversation_id: int,
    user_message_id: int,
    prompt_content: str | list[Any],
    model_id: str,
    model_endpoint_url: str,
    remote_user: str | None,
    remote_user_perm: str | None,
) -> ChatAuditEntry:
    prompt_text = extract_prompt_text(prompt_content)
    entry = ChatAuditEntry(
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        prompt_text=prompt_text,
        prompt_content_json=serialize_content(prompt_content),
        image_count=count_images(prompt_content),
        model_id=model_id,
        model_endpoint_url=model_endpoint_url,
        remote_user=remote_user,
        remote_user_perm=remote_user_perm,
        status="in_progress",
        started_at=_utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    append_jsonl(
        {
            "event": "exchange_started",
            "audit_id": entry.id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "prompt_text": prompt_text,
            "prompt_content": prompt_content,
            "image_count": entry.image_count,
            "model_id": model_id,
            "model_endpoint_url": model_endpoint_url,
            "remote_user": remote_user,
            "remote_user_perm": remote_user_perm,
            "started_at": entry.started_at.isoformat(),
        }
    )
    return entry


def record_exchange_completed(
    db: Session,
    audit_entry: ChatAuditEntry,
    *,
    assistant_message_id: int,
    response_text: str,
) -> None:
    audit_entry.assistant_message_id = assistant_message_id
    audit_entry.response_text = response_text
    audit_entry.status = "completed"
    audit_entry.completed_at = _utcnow()
    if audit_entry.error_message:
        audit_entry.error_message = None
    db.commit()
    db.refresh(audit_entry)

    append_jsonl(
        {
            "event": "exchange_completed",
            "audit_id": audit_entry.id,
            "conversation_id": audit_entry.conversation_id,
            "user_message_id": audit_entry.user_message_id,
            "assistant_message_id": assistant_message_id,
            "prompt_text": audit_entry.prompt_text,
            "response_text": response_text,
            "model_id": audit_entry.model_id,
            "status": "completed",
            "started_at": audit_entry.started_at.isoformat(),
            "completed_at": audit_entry.completed_at.isoformat(),
        }
    )


def record_exchange_failed(
    db: Session,
    audit_entry: ChatAuditEntry,
    *,
    error_message: str,
    partial_response: str | None = None,
) -> None:
    audit_entry.status = "error"
    audit_entry.error_message = error_message[:8000]
    audit_entry.response_text = partial_response
    audit_entry.completed_at = _utcnow()
    db.commit()
    db.refresh(audit_entry)

    append_jsonl(
        {
            "event": "exchange_failed",
            "audit_id": audit_entry.id,
            "conversation_id": audit_entry.conversation_id,
            "user_message_id": audit_entry.user_message_id,
            "prompt_text": audit_entry.prompt_text,
            "partial_response": partial_response,
            "error_message": error_message,
            "model_id": audit_entry.model_id,
            "status": "error",
            "started_at": audit_entry.started_at.isoformat(),
            "completed_at": audit_entry.completed_at.isoformat(),
        }
    )


def audit_entry_to_dict(entry: ChatAuditEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "conversation_id": entry.conversation_id,
        "user_message_id": entry.user_message_id,
        "assistant_message_id": entry.assistant_message_id,
        "prompt_text": entry.prompt_text,
        "prompt_content": parse_stored_content(entry.prompt_content_json),
        "response_text": entry.response_text,
        "image_count": entry.image_count,
        "model_id": entry.model_id,
        "model_endpoint_url": entry.model_endpoint_url,
        "remote_user": entry.remote_user,
        "remote_user_perm": entry.remote_user_perm,
        "status": entry.status,
        "error_message": entry.error_message,
        "started_at": entry.started_at.isoformat() if entry.started_at else None,
        "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
    }
