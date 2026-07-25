import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash

from slatesignal.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def new_session_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    return token, digest_token(token)


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=get_settings().session_days)
