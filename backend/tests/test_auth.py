from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User, UserRole
from app.core.config import get_settings
from app.core.auth import require_admin, require_vendor


def registration_payload(email: str = "vendor@example.com") -> dict[str, str]:
    return {
        "email": email,
        "full_name": "Fictional Vendor",
        "password": "correct-horse-battery-staple",
    }


def register(client: TestClient, email: str = "vendor@example.com") -> dict:
    response = client.post("/api/v1/auth/register", json=registration_payload(email))
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str = "vendor@example.com") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_vendor_registration_hashes_password(
    client: TestClient,
    db_session: Session,
) -> None:
    body = register(client, "  VENDOR@EXAMPLE.COM ")

    assert UUID(body["id"])
    assert body["email"] == "vendor@example.com"
    assert body["role"] == "vendor"
    assert "password" not in body

    user = db_session.scalar(select(User).where(User.email == "vendor@example.com"))
    assert user is not None
    assert user.password_hash.startswith("$argon2")
    assert "correct-horse-battery-staple" not in user.password_hash


def test_duplicate_registration_is_rejected(client: TestClient) -> None:
    register(client)

    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 409
    assert response.json() == {"detail": "An account with this email already exists"}


def test_public_registration_rejects_admin_escalation(client: TestClient) -> None:
    payload = registration_payload("attacker@example.com")
    payload["role"] = "admin"

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "attacker@example.com", "password": payload["password"]},
    )
    assert login_response.status_code == 401


def test_invalid_credentials_use_generic_error(client: TestClient) -> None:
    register(client)

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "vendor@example.com", "password": "wrong-password"},
    )
    unknown_user = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == {
        "detail": "Incorrect email or password"
    }


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_each_token_resolves_only_its_own_user(client: TestClient) -> None:
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")
    first_token = login(client, "first@example.com")
    second_token = login(client, "second@example.com")

    first_me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {first_token}"}
    )
    second_me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {second_token}"}
    )

    assert first_me.status_code == second_me.status_code == 200
    assert first_me.json()["id"] == first["id"]
    assert second_me.json()["id"] == second["id"]
    assert first_me.json()["id"] != second_me.json()["id"]


def test_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 401


def test_access_token_has_required_expiry_and_no_role_claim(client: TestClient) -> None:
    register(client)
    token = login(client)
    settings = get_settings()

    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )

    assert claims["type"] == "access"
    assert claims["sub"].startswith("user:")
    assert claims["exp"] - claims["iat"] == settings.access_token_expire_minutes * 60
    assert datetime.fromtimestamp(claims["exp"], timezone.utc) > datetime.now(timezone.utc)
    assert "role" not in claims


def test_expired_access_token_is_rejected(client: TestClient) -> None:
    user = register(client)
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {
            "sub": f"user:{user['id']}",
            "type": "access",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_role_dependencies_are_reusable_and_server_authoritative() -> None:
    vendor = User(
        email="vendor-role@example.com",
        full_name="Vendor Role Fixture",
        password_hash="not-used",
        role=UserRole.VENDOR,
    )
    admin = User(
        email="admin-role@example.com",
        full_name="Admin Role Fixture",
        password_hash="not-used",
        role=UserRole.ADMIN,
    )

    assert require_vendor(vendor) is vendor
    assert require_admin(admin) is admin
    with pytest.raises(HTTPException) as forbidden:
        require_admin(vendor)
    assert forbidden.value.status_code == 403


def test_database_role_constraint_accepts_only_known_roles(db_session: Session) -> None:
    user = User(
        email="admin-fixture@example.com",
        full_name="Local Admin Fixture",
        password_hash="not-used",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.flush()

    assert user.role is UserRole.ADMIN
