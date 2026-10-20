from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.modules.locations.schemas import WarehouseResponse
from app.modules.products.schemas import ProductResponse
from app.modules.suppliers.schemas import SupplierResponse


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    notes: Optional[str] = None
    items: List[PurchaseOrderItemCreate] = Field(..., min_length=1)


class PurchaseOrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    received_quantity: int
    unit_cost: Decimal
    tax_rate: Decimal
    line_total: Decimal
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class GoodsReceiptItemCreate(BaseModel):
    purchase_order_item_id: int
    quantity_received: int = Field(..., gt=0)


class GoodsReceiptCreate(BaseModel):
    notes: Optional[str] = None
    items: List[GoodsReceiptItemCreate] = Field(..., min_length=1)


class GoodsReceiptItemResponse(BaseModel):
    id: int
    product_id: int
    quantity_received: int
    unit_cost: Decimal
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class GoodsReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    purchase_order_id: int
    warehouse_id: int
    notes: Optional[str] = None
    created_at: datetime
    items: List[GoodsReceiptItemResponse]

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderResponse(BaseModel):
    id: int
    order_number: str
    supplier_id: int
    warehouse_id: int
    status: str
    subtotal: Decimal
    tax_total: Decimal
    total_amount: Decimal
    notes: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    supplier: Optional[SupplierResponse] = None
    warehouse: Optional[WarehouseResponse] = None
    items: List[PurchaseOrderItemResponse]
    receipts: List[GoodsReceiptResponse] = []

    model_config = ConfigDict(from_attributes=True)
