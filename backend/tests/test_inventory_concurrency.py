import asyncio
import pytest
from httpx import AsyncClient

from app.modules.users.models import User
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_stock_adjustments_and_immutable_ledger(client: AsyncClient, seed_data):
    admin: User = seed_data["admin"]
    headers = auth_header(admin)
    wh1 = seed_data["warehouse1"]
    prod = seed_data["product"]

    # 1. Positive adjustment +100
    res1 = await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 100,
            "adjustment_type": "POSITIVE_ADJUSTMENT",
            "reason": "Initial inventory count",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["data"]["on_hand"] == 100
    assert res1.json()["data"]["available"] == 100

    # 2. Negative adjustment -30
    res2 = await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 30,
            "adjustment_type": "NEGATIVE_ADJUSTMENT",
            "reason": "Damaged goods write-off",
        },
    )
    assert res2.status_code == 201
    assert res2.json()["data"]["on_hand"] == 70
    assert res2.json()["data"]["available"] == 70

    # 3. Reject negative adjustment exceeding available stock
    res3 = await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 100,
            "adjustment_type": "NEGATIVE_ADJUSTMENT",
            "reason": "Over-deduction attempt",
        },
    )
    assert res3.status_code == 409
    assert "Insufficient stock" in res3.json()["error"]["message"]

    # 4. Verify append-only movement ledger
    ledger_res = await client.get(
        f"/api/v1/inventory/movements?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert ledger_res.status_code == 200
    movements = ledger_res.json()["data"]["items"]
    assert len(movements) == 2  # 1 positive, 1 negative


@pytest.mark.asyncio
async def test_inter_warehouse_transfer_integrity(client: AsyncClient, seed_data):
    admin: User = seed_data["admin"]
    headers = auth_header(admin)
    wh1 = seed_data["warehouse1"]
    wh2 = seed_data["warehouse2"]
    prod = seed_data["product"]

    # Seed 50 units in WH1
    await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 50,
            "adjustment_type": "POSITIVE_ADJUSTMENT",
            "reason": "Seed WH1",
        },
    )

    # Transfer 20 units from WH1 to WH2
    tr_res = await client.post(
        "/api/v1/inventory/transfers",
        headers=headers,
        json={
            "source_warehouse_id": wh1.id,
            "destination_warehouse_id": wh2.id,
            "items": [{"product_id": prod.id, "quantity": 20}],
            "notes": "Relocation to West Coast Hub",
        },
    )
    assert tr_res.status_code == 201
    tr_data = tr_res.json()["data"]
    assert tr_data["status"] == "COMPLETED"
    assert tr_data["transfer_number"].startswith("TR-")

    # Verify WH1 stock is 30
    wh1_stock = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert wh1_stock.json()["data"]["items"][0]["on_hand"] == 30

    # Verify WH2 stock is 20
    wh2_stock = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh2.id}&product_id={prod.id}",
        headers=headers,
    )
    assert wh2_stock.json()["data"]["items"][0]["on_hand"] == 20


@pytest.mark.asyncio
async def test_concurrent_overselling_prevention(client: AsyncClient, seed_data):
    """
    Stress concurrency test:
    Setup stock = 10.
    Fire two competing requests trying to deduct 8 each simultaneously.
    Proves that exactly 1 request succeeds and the competing request is rejected with 409.
    Overselling is strictly prevented.
    """
    admin: User = seed_data["admin"]
    headers = auth_header(admin)
    wh1 = seed_data["warehouse1"]
    prod = seed_data["product"]

    # Initial stock: 10 units
    await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 10,
            "adjustment_type": "POSITIVE_ADJUSTMENT",
            "reason": "Setup for race condition test",
        },
    )

    req_payload = {
        "warehouse_id": wh1.id,
        "product_id": prod.id,
        "quantity": 8,
        "adjustment_type": "NEGATIVE_ADJUSTMENT",
        "reason": "Competing deduction",
    }

    # Execute concurrent competing deductions
    resp1, resp2 = await asyncio.gather(
        client.post("/api/v1/inventory/adjustments", headers=headers, json=req_payload),
        client.post("/api/v1/inventory/adjustments", headers=headers, json=req_payload),
    )

    statuses = [resp1.status_code, resp2.status_code]
    assert 201 in statuses
    assert 409 in statuses

    # Final stock level must be 2, never negative!
    final_stock = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert final_stock.json()["data"]["items"][0]["on_hand"] == 2
    assert final_stock.json()["data"]["items"][0]["available"] == 2
