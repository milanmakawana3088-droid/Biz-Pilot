from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, VersionMixin


class MovementType(str, Enum):
    PURCHASE_RECEIPT = "PURCHASE_RECEIPT"
    SALES_ISSUE = "SALES_ISSUE"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    POSITIVE_ADJUSTMENT = "POSITIVE_ADJUSTMENT"
    NEGATIVE_ADJUSTMENT = "NEGATIVE_ADJUSTMENT"
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    SUPPLIER_RETURN = "SUPPLIER_RETURN"


class TransferStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    RELEASED = "RELEASED"


class StockLevel(Base, TimestampMixin, VersionMixin):
    __tablename__ = "stock_levels"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    on_hand = Column(Integer, default=0, nullable=False)
    reserved = Column(Integer, default=0, nullable=False)

    warehouse = relationship("Warehouse", back_populates="stock_levels", lazy="selectin")
    product = relationship("Product", back_populates="stock_levels", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_stock_warehouse_product"),
        CheckConstraint("on_hand >= 0", name="ck_stock_on_hand_non_negative"),
        CheckConstraint("reserved >= 0", name="ck_stock_reserved_non_negative"),
        CheckConstraint("on_hand >= reserved", name="ck_stock_on_hand_gte_reserved"),
    )

    @hybrid_property
    def available(self) -> int:
        return self.on_hand - self.reserved


class StockMovement(Base):
    """
    Append-only immutable stock movement ledger.
    Never update balances without recording the movement in the exact same transaction.
    Never update or delete records in this table.
    """
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)  # Positive integer representing delta
    movement_type = Column(String(50), nullable=False, index=True)  # MovementType
    reference_document = Column(String(100), nullable=False, index=True)  # PO-..., SO-..., TR-..., ADJ-...
    unit_cost = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)

    actor_id = Column(Integer, nullable=True)
    actor_email = Column(String(255), nullable=True)
    reason = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    warehouse = relationship("Warehouse", lazy="selectin")
    product = relationship("Product", lazy="selectin")


class StockReservation(Base, TimestampMixin):
    __tablename__ = "stock_reservations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    status = Column(String(20), default=ReservationStatus.ACTIVE.value, nullable=False, index=True)

    sales_order = relationship("SalesOrder", back_populates="reservations")
    warehouse = relationship("Warehouse", lazy="selectin")
    product = relationship("Product", lazy="selectin")


class InventoryTransfer(Base, TimestampMixin, VersionMixin):
    __tablename__ = "inventory_transfers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transfer_number = Column(String(50), unique=True, index=True, nullable=False)
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)

    status = Column(String(20), default=TransferStatus.DRAFT.value, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)

    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id], lazy="selectin")
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id], lazy="selectin")
    items = relationship("InventoryTransferItem", back_populates="transfer", cascade="all, delete-orphan", lazy="selectin")


class InventoryTransferItem(Base, TimestampMixin):
    __tablename__ = "inventory_transfer_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transfer_id = Column(Integer, ForeignKey("inventory_transfers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)

    transfer = relationship("InventoryTransfer", back_populates="items")
    product = relationship("Product", lazy="selectin")
