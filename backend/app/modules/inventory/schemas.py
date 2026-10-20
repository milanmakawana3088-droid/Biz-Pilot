from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.modules.inventory.models import MovementType, TransferStatus
from app.modules.products.schemas import ProductResponse


class StockLevelResponse(BaseModel):
    id: int
    warehouse_id: int
    product_id: int
    on_hand: int
    reserved: int
    available: int
    product: Optional[ProductResponse] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockMovementResponse(BaseModel):
    id: int
    warehouse_id: int
    product_id: int
    quantity: int
    movement_type: str
    reference_document: str
    unit_cost: Decimal
    actor_email: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class StockAdjustmentRequest(BaseModel):
    warehouse_id: int
    product_id: int
    quantity: int = Field(..., gt=0, description="Positive quantity to adjust")
    adjustment_type: str = Field(..., description="POSITIVE_ADJUSTMENT or NEGATIVE_ADJUSTMENT")
    reason: str = Field(..., min_length=3, max_length=255, description="Mandatory reason for reconciliation")


class TransferItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class TransferCreateRequest(BaseModel):
    source_warehouse_id: int
    destination_warehouse_id: int
    items: List[TransferItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class TransferItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TransferResponse(BaseModel):
    id: int
    transfer_number: str
    source_warehouse_id: int
    destination_warehouse_id: int
    status: str
    notes: Optional[str] = None
    items: List[TransferItemResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
