import pytest
from httpx import AsyncClient

from app.modules.users.models import User
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_login_success_and_token_issue(client: AsyncClient, seed_data):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.io", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["user"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_login_invalid_password_rejected(client: AsyncClient, seed_data):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.io", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_current_user_me_endpoint(client: AsyncClient, seed_data):
    admin: User = seed_data["admin"]
    headers = auth_header(admin)

    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "admin@test.io"
    assert "product:write" in data["permissions"]


@pytest.mark.asyncio
async def test_warehouse_access_isolation_enforcement(client: AsyncClient, seed_data):
    manager: User = seed_data["manager"]
    wh1 = seed_data["warehouse1"]
    wh2 = seed_data["warehouse2"]
    prod = seed_data["product"]

    # Manager has access only to WH1
    headers = auth_header(manager, warehouse_ids=[wh1.id])

    # 1. Allowed operation on authorized WH1
    ok_res = await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 10,
            "adjustment_type": "POSITIVE_ADJUSTMENT",
            "reason": "Initial stock setup",
        },
    )
    assert ok_res.status_code == 201

    # 2. Blocked operation on unauthorized WH2
    blocked_res = await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh2.id,
            "product_id": prod.id,
            "quantity": 5,
            "adjustment_type": "POSITIVE_ADJUSTMENT",
            "reason": "Intruder attempt",
        },
    )
    assert blocked_res.status_code == 403
    assert "does not have authorized access to warehouse" in blocked_res.json()["error"]["message"]
