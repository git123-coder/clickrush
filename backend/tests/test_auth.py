"""
tests/test_auth.py
────────────────────
Automated tests for Day 1 authentication functionality.

Covers:
  - Invalid credentials
"""

import pytest

def test_login_invalid_password(client, registered_user):
    resp = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": "wrongpassword123",
    })
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()


def test_login_invalid_email(client):
    resp = client.post("/api/auth/login", json={
        "email": "not.registered@clickrush.dev",
        "password": "anypassword",
    })
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()
