"""
app/core/security.py
────────────────────
Password hashing and JWT token helpers.

Design decisions:
  - bcrypt is the industry standard for password hashing.
    It is intentionally slow (cost factor) to defeat brute-force attacks.
    We use the bcrypt library directly (no passlib wrapper) for compatibility
    with bcrypt 4.x+.
    Plaintext passwords are NEVER stored or logged.

  - JWT tokens carry only the user's UUID (subject = "sub").
    We avoid embedding sensitive data (email, roles) in the payload
    because tokens are signed but NOT encrypted — anyone can decode them.

  - Tokens expire after JWT_ACCESS_TOKEN_EXPIRE_MINUTES to limit the window
    of exposure if a token is ever leaked.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# ── Password hashing ─────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plaintext matches the bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(subject: Any) -> str:
    """
    Create a signed JWT token.

    Args:
        subject: The value to embed as the "sub" claim (typically user UUID).

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Decode and validate a JWT token.

    Returns:
        The "sub" claim (user UUID as string).

    Raises:
        JWTError: If the token is invalid, expired, or tampered with.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    subject: str | None = payload.get("sub")
    if subject is None:
        raise JWTError("Token missing 'sub' claim")
    return subject
