# Central registry of all domain models for SQLAlchemy metadata and Alembic migrations
from app.db.base import Base
from app.common.numbering import DocumentSequence
from app.modules.audit.models import AuditLog, IdempotencyRecord, OutboxEvent
from app.modules.users.models import User, UserWarehouseAccess
from app.modules.locations.models import Location, Warehouse
from app.modules.products.models import ProductCategory, UnitOfMeasure, Product
from app.modules.customers.models import Customer
from app.modules.suppliers.models import Supplier
from app.modules.inventory.models import (
    StockLevel,
    StockMovement,
    StockReservation,
    InventoryTransfer,
    InventoryTransferItem,
)
from app.modules.purchasing.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceipt,
    GoodsReceiptItem,
)
from app.modules.sales.models import (
    SalesOrder,
    SalesOrderItem,
    Shipment,
    ShipmentItem,
)

__all__ = [
    "Base",
    "DocumentSequence",
    "AuditLog",
    "IdempotencyRecord",
    "OutboxEvent",
    "User",
    "UserWarehouseAccess",
    "Location",
    "Warehouse",
    "ProductCategory",
    "UnitOfMeasure",
    "Product",
    "Customer",
    "Supplier",
    "StockLevel",
    "StockMovement",
    "StockReservation",
    "InventoryTransfer",
    "InventoryTransferItem",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "GoodsReceipt",
    "GoodsReceiptItem",
    "SalesOrder",
    "SalesOrderItem",
    "Shipment",
    "ShipmentItem",
]
