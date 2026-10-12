from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class TokenEncryptionError(Exception):
    pass


def _encryption_key_path() -> Path:
    custom = settings.model_token_encryption_key_file
    if custom:
        return custom.resolve()
    return (settings.project_root / "data" / ".token_encryption_key").resolve()


def resolve_encryption_key() -> str:
    """
    Fernet key for token encryption at rest.

    Priority: MODEL_TOKEN_ENCRYPTION_KEY env → persisted file on project storage →
    generate and persist a new key (typical Cloudera Workbench path).
    """
    if settings.model_token_encryption_key.strip():
        return settings.model_token_encryption_key.strip()

    path = _encryption_key_path()
    if path.is_file():
        key = path.read_text(encoding="utf-8").strip()
        if key:
            return key

    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key().decode("ascii")
    path.write_text(key, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


@lru_cache
def _fernet() -> Fernet:
    key = resolve_encryption_key()
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise TokenEncryptionError(
            "MODEL_TOKEN_ENCRYPTION_KEY is not a valid Fernet key"
        ) from exc


def encrypt_token(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_token(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenEncryptionError("Stored model token could not be decrypted") from exc


def mask_token_configured(has_token: bool) -> str | None:
    """Always masked; never reveal length or suffix of the secret."""
    if not has_token:
        return None
    return "••••••••••••"
