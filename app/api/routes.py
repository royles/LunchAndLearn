import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message
from app.db.session import SessionLocal, get_db
from app.schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    ModelSettingsPublic,
    ModelSettingsUpdate,
)
from app.services.crypto import TokenEncryptionError
from app.services.model_settings import (
    get_or_create_settings,
    resolve_for_inference,
    to_public,
    update_settings,
)
from app.services.llm import (
    build_user_content,
    parse_stored_content,
    serialize_content,
    stream_chat_completion,
    to_openai_messages,
)

router = APIRouter(prefix="/api/v1")


@router.get("/model-settings", response_model=ModelSettingsPublic)
def get_model_settings(db: Session = Depends(get_db)) -> dict:
    row = get_or_create_settings(db)
    return to_public(row)


@router.put("/model-settings", response_model=ModelSettingsPublic)
def put_model_settings(
    body: ModelSettingsUpdate, db: Session = Depends(get_db)
) -> dict:
    clear_token = body.model_token is not None and body.model_token.strip() == ""
    token_to_set = None if clear_token or body.model_token is None else body.model_token
    try:
        row = update_settings(
            db,
            endpoint_url=body.model_endpoint_url,
            model_id=body.model_id,
            model_token=token_to_set,
            clear_token=clear_token,
        )
    except TokenEncryptionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return to_public(row)


@router.get("/me")
def current_user(request: Request) -> dict[str, str | None]:
    return {
        "remote_user": request.headers.get("REMOTE-USER"),
        "remote_user_perm": request.headers.get("REMOTE-USER-PERM"),
    }


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)) -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())
    return list(db.scalars(stmt).all())


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(
    body: ConversationCreate, db: Session = Depends(get_db)
) -> Conversation:
    conv = Conversation(title=body.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    body: ConversationUpdate,
    db: Session = Depends(get_db),
) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = body.title
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conv)
    return conv


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)) -> None:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: int, db: Session = Depends(get_db)) -> list[dict]:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [_message_to_out(m) for m in conv.messages]


def _message_to_out(message: Message) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": parse_stored_content(message.content),
        "created_at": message.created_at,
    }


@router.post("/conversations/{conversation_id}/chat")
async def chat_stream(
    conversation_id: int,
    body: ChatRequest,
    db: Session = Depends(get_db),
):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_content = build_user_content(body.message, body.images)
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=serialize_content(user_content),
    )
    db.add(user_msg)
    conv.updated_at = datetime.now(timezone.utc)
    if conv.title == "New chat":
        conv.title = body.message.strip()[:80] or "New chat"
    db.commit()
    db.refresh(user_msg)

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    history_rows = list(db.scalars(stmt).all())
    history: list[tuple[str, str | list]] = []
    for row in history_rows:
        history.append((row.role, parse_stored_content(row.content)))

    openai_messages = to_openai_messages(history)
    try:
        resolved = resolve_for_inference(db)
    except TokenEncryptionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    async def event_generator():
        assistant_parts: list[str] = []
        try:
            async for token in stream_chat_completion(
                openai_messages, resolved, body.model
            ):
                assistant_parts.append(token)
                payload = json.dumps({"type": "token", "content": token})
                yield f"data: {payload}\n\n"
        except Exception as exc:
            err = json.dumps({"type": "error", "message": str(exc)})
            yield f"data: {err}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"
            return

        full_text = "".join(assistant_parts)
        save_db = SessionLocal()
        try:
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_text,
            )
            save_db.add(assistant_msg)
            c = save_db.get(Conversation, conversation_id)
            if c:
                c.updated_at = datetime.now(timezone.utc)
            save_db.commit()
            save_db.refresh(assistant_msg)
            done_payload = json.dumps(
                {
                    "type": "done",
                    "message": _message_to_out(assistant_msg),
                }
            )
            yield f"data: {done_payload}\n\n"
        finally:
            save_db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
