import pytest
from httpx import AsyncClient

from app.modules.users.models import User
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_purchase_order_full_lifecycle_and_partial_receipt(client: AsyncClient, seed_data):
    admin: User = seed_data["admin"]
    headers = auth_header(admin)
    wh1 = seed_data["warehouse1"]
    prod = seed_data["product"]
    supp = seed_data["supplier"]

    # 1. Create Draft PO for 100 units
    create_res = await client.post(
        "/api/v1/purchase-orders",
        headers=headers,
        json={
            "supplier_id": supp.id,
            "warehouse_id": wh1.id,
            "notes": "Q4 Bulk Restock",
            "items": [
                {
                    "product_id": prod.id,
                    "quantity": 100,
                    "unit_cost": "10.00",
                    "tax_rate": "5.00",
                }
            ],
        },
    )
    assert create_res.status_code == 201
    po = create_res.json()["data"]
    assert po["status"] == "DRAFT"
    assert po["order_number"].startswith("PO-")
    po_item_id = po["items"][0]["id"]

    # 2. Cannot receive goods on DRAFT PO
    bad_rec = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive",
        headers=headers,
        json={
            "items": [{"purchase_order_item_id": po_item_id, "quantity_received": 50}],
        },
    )
    assert bad_rec.status_code == 422

    # 3. Approve PO
    appr_res = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/approve",
        headers=headers,
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["data"]["status"] == "APPROVED"

    # 4. Partial Goods Receipt: 40 units
    rec1_res = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive",
        headers=headers,
        json={
            "notes": "First partial batch",
            "items": [{"purchase_order_item_id": po_item_id, "quantity_received": 40}],
        },
    )
    assert rec1_res.status_code == 200
    grn1 = rec1_res.json()["data"]
    assert grn1["receipt_number"].startswith("GRN-")

    # Verify PO status is PARTIALLY_RECEIVED
    po_check = await client.get(f"/api/v1/purchase-orders/{po['id']}", headers=headers)
    assert po_check.json()["data"]["status"] == "PARTIALLY_RECEIVED"

    # Verify stock on hand in WH1 increased to 40
    stock_res = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert stock_res.json()["data"]["items"][0]["on_hand"] == 40

    # 5. Over-receipt attempt: ordered 100, received 40, attempting to receive 70 (total 110)
    over_rec = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive",
        headers=headers,
        json={
            "items": [{"purchase_order_item_id": po_item_id, "quantity_received": 70}],
        },
    )
    assert over_rec.status_code == 400
    assert "Over-receipt rejected" in over_rec.json()["error"]["message"]

    # 6. Complete remaining receipt: 60 units
    rec2_res = await client.post(
        f"/api/v1/purchase-orders/{po['id']}/receive",
        headers=headers,
        json={
            "notes": "Final batch",
            "items": [{"purchase_order_item_id": po_item_id, "quantity_received": 60}],
        },
    )
    assert rec2_res.status_code == 200

    # Verify PO status is RECEIVED
    po_final = await client.get(f"/api/v1/purchase-orders/{po['id']}", headers=headers)
    assert po_final.json()["data"]["status"] == "RECEIVED"

    # Final stock is 100
    stock_final = await client.get(
        f"/api/v1/inventory/stock-levels?warehouse_id={wh1.id}&product_id={prod.id}",
        headers=headers,
    )
    assert stock_final.json()["data"]["items"][0]["on_hand"] == 100
