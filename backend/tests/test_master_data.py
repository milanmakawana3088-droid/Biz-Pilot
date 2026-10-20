import pytest
from httpx import AsyncClient

from app.modules.users.models import User
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_product_crud_and_duplicate_sku_prevention(client: AsyncClient, seed_data):
    admin: User = seed_data["admin"]
    headers = auth_header(admin)

    # 1. Create product
    create_res = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "sku": "SKU-GADGET-99",
            "name": "Super Gadget Pro",
            "uom_id": seed_data["product"].uom_id,
            "cost_price": "45.50",
            "selling_price": "79.99",
            "tax_rate": "10.00",
            "reorder_level": 15,
        },
    )
    assert create_res.status_code == 201
    prod_data = create_res.json()["data"]
    assert prod_data["sku"] == "SKU-GADGET-99"

    # 2. Reject duplicate SKU
    dup_res = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "sku": "SKU-GADGET-99",
            "name": "Duplicate Attempt",
            "uom_id": seed_data["product"].uom_id,
            "cost_price": "10.00",
            "selling_price": "20.00",
            "tax_rate": "0.00",
        },
    )
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["error"]["message"]

    # 3. List products with search
    list_res = await client.get("/api/v1/products?search=Gadget", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "SKU-GADGET-99"

    # 4. Update product
    update_res = await client.patch(
        f"/api/v1/products/{prod_data['id']}",
        headers=headers,
        json={"name": "Super Gadget Pro Max", "selling_price": "89.99"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Super Gadget Pro Max"
