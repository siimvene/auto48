"""Password hashing and JWT token utilities.

Uses pwdlib[argon2] for password hashing (avoids bcrypt 72-byte truncation and
passlib/bcrypt.__about__ incompatibility) and PyJWT for token encoding.

Secret and expiry are read from Settings — never hard-coded at call sites.
"""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from auto48.config import get_settings

_password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Return an argon2 hash of the given plaintext password."""
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*; False otherwise."""
    return _password_hash.verify(plain, hashed)


def create_access_token(sub: str, expires: timedelta | None = None) -> str:
    """Encode a signed JWT with the given subject claim.

    Args:
        sub: Token subject (use ``str(user.id)``).
        expires: Optional override for token lifetime; falls back to
            ``settings.jwt_expire_minutes``.

    Returns:
        Compact JWT string.
    """
    settings = get_settings()
    if expires is None:
        expires = timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(tz=UTC)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.

    Raises ``jwt.PyJWTError`` on invalid/expired tokens — callers should
    convert that to an HTTP 401.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
