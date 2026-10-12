from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class TokenEncryptionError(Exception):
    pass


@lru_cache
def _fernet() -> Fernet:
    key = settings.model_token_encryption_key
    if not key:
        raise TokenEncryptionError(
            "MODEL_TOKEN_ENCRYPTION_KEY is not set. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise TokenEncryptionError("MODEL_TOKEN_ENCRYPTION_KEY is not a valid Fernet key") from exc


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
