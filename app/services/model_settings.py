from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ModelSettings
from app.services.crypto import (
    decrypt_token,
    encrypt_token,
    mask_token_configured,
    resolve_encryption_key,
)

SETTINGS_ROW_ID = 1


@dataclass(frozen=True)
class ResolvedModelConfig:
    endpoint_url: str
    model_id: str
    api_token: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_settings(db: Session) -> ModelSettings:
    row = db.get(ModelSettings, SETTINGS_ROW_ID)
    if row is None:
        token_ciphertext = None
        if settings.llm_api_key and settings.llm_api_key != "not-needed":
            try:
                resolve_encryption_key()
                token_ciphertext = encrypt_token(settings.llm_api_key)
            except Exception:
                token_ciphertext = None
        row = ModelSettings(
            id=SETTINGS_ROW_ID,
            endpoint_url=settings.llm_base_url,
            model_id=settings.llm_model,
            token_ciphertext=token_ciphertext,
            updated_at=_utcnow(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def to_public(row: ModelSettings) -> dict:
    has_token = bool(row.token_ciphertext)
    return {
        "model_endpoint_url": row.endpoint_url,
        "model_id": row.model_id,
        "model_token_masked": mask_token_configured(has_token),
        "has_model_token": has_token,
        "supports_multimodal": True,
        "supports_streaming": True,
        "updated_at": row.updated_at,
    }


def update_settings(
    db: Session,
    *,
    endpoint_url: str,
    model_id: str,
    model_token: str | None = None,
    clear_token: bool = False,
) -> ModelSettings:
    row = get_or_create_settings(db)
    row.endpoint_url = endpoint_url.strip()
    row.model_id = model_id.strip()
    row.updated_at = _utcnow()

    if clear_token:
        row.token_ciphertext = None
    elif model_token is not None and model_token.strip():
        row.token_ciphertext = encrypt_token(model_token.strip())

    db.commit()
    db.refresh(row)
    return row


def resolve_for_inference(db: Session) -> ResolvedModelConfig:
    row = get_or_create_settings(db)
    token = ""
    if row.token_ciphertext:
        token = decrypt_token(row.token_ciphertext)
    if not token:
        token = "not-needed"
    return ResolvedModelConfig(
        endpoint_url=row.endpoint_url,
        model_id=row.model_id,
        api_token=token,
    )
