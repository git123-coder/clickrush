"""
app/services/user_service.py
─────────────────────────────
Database CRUD helpers for the User model.

Why a service layer?
  - Keeps business logic out of route handlers.
  - Route handlers handle HTTP concerns (status codes, request parsing).
  - Services handle data concerns (DB queries, validation logic).
  - Makes testing easier — services can be tested without HTTP.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import SignupRequest


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the User with the given email, or None."""
    return db.scalar(select(User).where(User.email == email))


def get_user_by_username(db: Session, username: str) -> User | None:
    """Return the User with the given username, or None."""
    return db.scalar(select(User).where(User.username == username))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Return the User with the given UUID, or None."""
    return db.get(User, user_id)


def create_user(db: Session, data: SignupRequest) -> User:
    """
    Persist a new User to the database.

    Hashes the password before storage — plaintext password is discarded
    immediately after hashing and is never written to the DB.
    """
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
