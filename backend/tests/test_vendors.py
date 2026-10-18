from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.models.identity import User, UserRole, Vendor


def register_and_login(client: TestClient, email: str) -> tuple[dict, dict[str, str]]:
    password = "correct-horse-battery-staple"
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Vendor Fixture", "password": password},
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return registration.json(), {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


def profile_payload(company_name: str = "Example Trading Ltd") -> dict[str, str]:
    return {
        "company_name": company_name,
        "registration_number": "REG-001",
        "contact_email": "operations@example.com",
        "phone": "+880 1700-000000",
        "address": "100 Fictional Commerce Road, Dhaka",
    }


def test_vendor_can_create_own_profile(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = register_and_login(client, "create-profile@example.com")

    response = client.post("/api/v1/vendors/me", json=profile_payload(), headers=headers)

    assert response.status_code == 201
    assert response.json()["owner_user_id"] == user["id"]
    assert response.json()["company_name"] == "Example Trading Ltd"
    stored = db_session.scalar(
        select(Vendor).where(Vendor.owner_user_id == user["id"])
    )
    assert stored is not None
    assert stored.contact_email == "operations@example.com"


def test_vendor_can_read_own_profile(client: TestClient) -> None:
    _, headers = register_and_login(client, "read-profile@example.com")
    created = client.post(
        "/api/v1/vendors/me", json=profile_payload(), headers=headers
    ).json()

    response = client.get("/api/v1/vendors/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == created


def test_vendor_can_partially_update_own_profile(client: TestClient) -> None:
    _, headers = register_and_login(client, "update-profile@example.com")
    client.post("/api/v1/vendors/me", json=profile_payload(), headers=headers)

    response = client.patch(
        "/api/v1/vendors/me",
        json={"company_name": "Updated Fictional Trading Ltd", "phone": "+8801711111111"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["company_name"] == "Updated Fictional Trading Ltd"
    assert response.json()["phone"] == "+8801711111111"
    assert response.json()["registration_number"] == "REG-001"


def test_vendor_profile_endpoints_require_authentication(client: TestClient) -> None:
    assert client.post("/api/v1/vendors/me", json=profile_payload()).status_code == 401
    assert client.get("/api/v1/vendors/me").status_code == 401
    assert client.patch(
        "/api/v1/vendors/me", json={"company_name": "Unauthorized"}
    ).status_code == 401


def test_admin_cannot_manage_a_vendor_profile(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = User(
        email="profile-admin@example.com",
        full_name="Profile Admin Fixture",
        password_hash="not-used",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    token, _ = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post(
        "/api/v1/vendors/me", json=profile_payload(), headers=headers
    ).status_code == 403
    assert client.get("/api/v1/vendors/me", headers=headers).status_code == 403
    assert client.patch(
        "/api/v1/vendors/me", json={"company_name": "Forbidden"}, headers=headers
    ).status_code == 403


def test_duplicate_vendor_profile_is_rejected(client: TestClient) -> None:
    _, headers = register_and_login(client, "duplicate-profile@example.com")
    first = client.post("/api/v1/vendors/me", json=profile_payload(), headers=headers)

    duplicate = client.post(
        "/api/v1/vendors/me",
        json=profile_payload("Replacement Company"),
        headers=headers,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Vendor profile already exists"}


def test_cross_vendor_profiles_are_isolated(client: TestClient) -> None:
    first_user, first_headers = register_and_login(client, "first-profile@example.com")
    second_user, second_headers = register_and_login(client, "second-profile@example.com")
    first_profile = client.post(
        "/api/v1/vendors/me",
        json=profile_payload("First Company"),
        headers=first_headers,
    ).json()
    second_profile = client.post(
        "/api/v1/vendors/me",
        json=profile_payload("Second Company"),
        headers=second_headers,
    ).json()

    update = client.patch(
        "/api/v1/vendors/me",
        json={"company_name": "First Company Updated"},
        headers=first_headers,
    )
    second_read = client.get("/api/v1/vendors/me", headers=second_headers)

    assert first_profile["owner_user_id"] == first_user["id"]
    assert second_profile["owner_user_id"] == second_user["id"]
    assert first_profile["id"] != second_profile["id"]
    assert update.json()["company_name"] == "First Company Updated"
    assert second_read.json()["company_name"] == "Second Company"


def test_profile_input_validation_rejects_blank_and_invalid_values(
    client: TestClient,
) -> None:
    _, headers = register_and_login(client, "validation-profile@example.com")
    payload = profile_payload()
    payload["company_name"] = "   "
    payload["phone"] = "call-me"

    response = client.post("/api/v1/vendors/me", json=payload, headers=headers)

    assert response.status_code == 422
    assert client.get("/api/v1/vendors/me", headers=headers).status_code == 404
