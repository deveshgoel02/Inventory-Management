import datetime
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Using the `bcrypt` library directly rather than passlib: passlib is
# unmaintained and its bcrypt backend-detection shim is broken against
# bcrypt>=4.1 (raises on the "password too long" self-test it runs at
# import time), which bites on any current Python/bcrypt install.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    truncated = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(truncated, hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject, datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access", extra_claims
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, datetime.timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES), "refresh", None
    )


def _create_token(
    subject: str, expires_delta: datetime.timedelta, token_type: str, extra_claims: dict[str, Any] | None
) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    to_encode = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
