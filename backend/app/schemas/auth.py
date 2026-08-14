"""
app/schemas/auth.py
───────────────────
Pydantic schemas for authentication request/response bodies.
"""

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Body for POST /api/auth/signup."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="3–50 characters, letters/digits/underscore only.",
    )
    email: EmailStr = Field(..., description="Valid email address.")
    password: str = Field(
        ...,
        min_length=8,
        description="Minimum 8 characters.",
    )


class LoginRequest(BaseModel):
    """Body for POST /api/auth/login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response for a successful login."""

    access_token: str
    token_type: str = "bearer"
