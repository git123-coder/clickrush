"""
app/api/deps.py
───────────────
Reusable FastAPI dependencies for authentication.

get_current_user():
  1. Reads the Authorization header and extracts the Bearer token.
  2. Decodes and validates the JWT signature + expiry.
  3. Extracts the user UUID from the "sub" claim.
  4. Fetches the user from PostgreSQL to verify they still exist.
  5. Returns the authenticated User ORM object.
  6. Raises HTTP 401 for any failure so route handlers stay clean.

Why this approach?
  - FastAPI's Depends() system makes it trivial to protect any endpoint.
  - Centralising auth logic here means changes propagate everywhere at once.
  - Fetching from DB on every request ensures deactivated users are rejected
    immediately (token revocation via user deletion works out of the box).
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.user_service import get_user_by_id

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency: decode the Bearer JWT and return the active User.

    Raises HTTP 401 if the token is missing, invalid, expired, or the
    referenced user no longer exists in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id_str = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user
