"""
app/schemas/user.py
───────────────────
Pydantic schemas that represent the public-facing User resource.

Why separate schemas from ORM models?
  - ORM models (SQLAlchemy) define the database structure.
  - Schemas (Pydantic) define the API contract.
  - This separation means we can evolve the DB schema without accidentally
    exposing internal fields (like password_hash) in API responses.
  - Pydantic also gives us automatic validation and OpenAPI documentation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """
    Safe public representation of a User.
    password_hash is deliberately absent.
    """

    id: uuid.UUID
    username: str
    email: str
    created_at: datetime

    # orm_mode (v1) → from_attributes (v2): allows Pydantic to read
    # attributes from SQLAlchemy ORM instances directly.
    model_config = ConfigDict(from_attributes=True)
