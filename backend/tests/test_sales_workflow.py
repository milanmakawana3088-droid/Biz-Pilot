import pytest
from httpx import AsyncClient

from app.modules.users.models import User
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_sales_order_reservation_and_shipment_lifecycle(client: AsyncClient, seed_data):
    admin: User = seed_data["admin"]
    headers = auth_header(admin)
    wh1 = seed_data["warehouse1"]
    prod = seed_data["product"]
    cust = seed_data["customer"]

    # Seed 50 units into stock
    await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 50,
            "adjustment_type": "POSITIVE_ADJUSTMENT",
            "reason": "Initial balance",
        },
    )

    # 1. Create Draft SO for 30 units
    so_res = await client.post(
        "/api/v1/sales-orders",
        headers=headers,
        json={
            "customer_id": cust.id,
            "warehouse_id": wh1.id,
            "notes": "Rush client order",
            "items": [
                {
                    "product_id": prod.id,
                    "quantity": 30,
                    "unit_price": "25.00",
                    "tax_rate": "8.00",
                }
            ],
        },
    )
    assert so_res.status_code == 201
    so = so_res.json()["data"]
    assert so["status"] == "DRAFT"
    so_item_id = so["items"][0]["id"]

    # 2. Confirm SO -> Reserves 30 units
    conf_res = await client.post(f"/api/v1/sales-orders/{so['id']}/confirm", headers=headers)
    assert conf_res.status_code == 200
    assert conf_res.json()["data"]["status"] == "CONFIRMED"

    # Verify Stock level: on_hand=50, reserved=30, available=20
    stock_chk = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    stock_data = stock_chk.json()["data"]["items"][0]
    assert stock_data["on_hand"] == 50
    assert stock_data["reserved"] == 30
    assert stock_data["available"] == 20

    # 3. Ship order with Idempotency Key
    ship_headers = {**headers, "Idempotency-Key": "test-idem-shipment-unique-001"}
    ship_payload = {
        "tracking_number": "TRK-987654",
        "carrier": "FedEx Priority",
        "items": [{"sales_order_item_id": so_item_id, "quantity_shipped": 30}],
    }

    ship_res1 = await client.post(
        f"/api/v1/sales-orders/{so['id']}/ship",
        headers=ship_headers,
        json=ship_payload,
    )
    assert ship_res1.status_code == 200
    shp_data = ship_res1.json()["data"]
    assert shp_data["shipment_number"].startswith("SHP-")

    # 4. Verify stock after shipment: on_hand=20, reserved=0, available=20
    stock_after = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    stock_after_data = stock_after.json()["data"]["items"][0]
    assert stock_after_data["on_hand"] == 20
    assert stock_after_data["reserved"] == 0
    assert stock_after_data["available"] == 20

    # 5. Idempotent Retry: Send the exact same request again with the same idempotency key
    ship_res2 = await client.post(
        f"/api/v1/sales-orders/{so['id']}/ship",
        headers=ship_headers,
        json=ship_payload,
    )
    assert ship_res2.status_code == 200
    assert ship_res2.headers.get("X-Cache-Lookup") == "HIT-IDEMPOTENCY"

    # Stock must STILL be 20, NOT deducted twice!
    stock_after_retry = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert stock_after_retry.json()["data"]["items"][0]["on_hand"] == 20


@pytest.mark.asyncio
async def test_sales_order_cancellation_releases_reservation(client: AsyncClient, seed_data):
    admin: User = seed_data["admin"]
    headers = auth_header(admin)
    wh1 = seed_data["warehouse1"]
    prod = seed_data["product"]
    cust = seed_data["customer"]

    # Seed 20 units
    await client.post(
        "/api/v1/inventory/adjustments",
        headers=headers,
        json={
            "warehouse_id": wh1.id,
            "product_id": prod.id,
            "quantity": 20,
            "adjustment_type": "POSITIVE_ADJUSTMENT",
            "reason": "Seed stock",
        },
    )

    # Create and Confirm order for 15 units
    so_res = await client.post(
        "/api/v1/sales-orders",
        headers=headers,
        json={
            "customer_id": cust.id,
            "warehouse_id": wh1.id,
            "items": [{"product_id": prod.id, "quantity": 15, "unit_price": "20.00"}],
        },
    )
    so_id = so_res.json()["data"]["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm", headers=headers)

    # Reserved = 15, Available = 5
    st1 = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert st1.json()["data"]["items"][0]["reserved"] == 15
    assert st1.json()["data"]["items"][0]["available"] == 5

    # Cancel sales order
    cancel_res = await client.post(f"/api/v1/sales-orders/{so_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # Stock reservations must be released: Reserved = 0, Available = 20
    st2 = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert st2.json()["data"]["items"][0]["reserved"] == 0
    assert st2.json()["data"]["items"][0]["available"] == 20
