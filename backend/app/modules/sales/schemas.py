from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.modules.customers.schemas import CustomerResponse
from app.modules.locations.schemas import WarehouseResponse
from app.modules.products.schemas import ProductResponse


class SalesOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)


class SalesOrderCreate(BaseModel):
    customer_id: int
    warehouse_id: int
    notes: Optional[str] = None
    items: List[SalesOrderItemCreate] = Field(..., min_length=1)


class SalesOrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    shipped_quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ShipmentItemCreate(BaseModel):
    sales_order_item_id: int
    quantity_shipped: int = Field(..., gt=0)


class ShipmentCreate(BaseModel):
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    items: List[ShipmentItemCreate] = Field(..., min_length=1)


class ShipmentItemResponse(BaseModel):
    id: int
    product_id: int
    quantity_shipped: int
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ShipmentResponse(BaseModel):
    id: int
    shipment_number: str
    sales_order_id: int
    warehouse_id: int
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    created_at: datetime
    items: List[ShipmentItemResponse]

    model_config = ConfigDict(from_attributes=True)


class SalesOrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    warehouse_id: int
    status: str
    subtotal: Decimal
    tax_total: Decimal
    total_amount: Decimal
    notes: Optional[str] = None
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    customer: Optional[CustomerResponse] = None
    warehouse: Optional[WarehouseResponse] = None
    items: List[SalesOrderItemResponse]
    shipments: List[ShipmentResponse] = []

    model_config = ConfigDict(from_attributes=True)
