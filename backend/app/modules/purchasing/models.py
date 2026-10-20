from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, VersionMixin


class PurchaseOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class PurchaseOrder(Base, TimestampMixin, VersionMixin):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)

    status = Column(String(30), default=PurchaseOrderStatus.DRAFT.value, nullable=False, index=True)

    subtotal = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    tax_total = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    total_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)

    notes = Column(Text, nullable=True)
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)

    supplier = relationship("Supplier", back_populates="purchase_orders", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin")
    receipts = relationship("GoodsReceipt", back_populates="purchase_order", lazy="selectin")


class PurchaseOrderItem(Base, TimestampMixin):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    received_quantity = Column(Integer, default=0, nullable=False)

    unit_cost = Column(Numeric(14, 4), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    line_total = Column(Numeric(14, 4), nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", lazy="selectin")


class GoodsReceipt(Base, TimestampMixin):
    __tablename__ = "goods_receipts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    receipt_number = Column(String(50), unique=True, index=True, nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)

    notes = Column(Text, nullable=True)
    received_by = Column(Integer, nullable=True)

    purchase_order = relationship("PurchaseOrder", back_populates="receipts")
    warehouse = relationship("Warehouse", lazy="selectin")
    items = relationship("GoodsReceiptItem", back_populates="receipt", cascade="all, delete-orphan", lazy="selectin")


class GoodsReceiptItem(Base, TimestampMixin):
    __tablename__ = "goods_receipt_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    goods_receipt_id = Column(Integer, ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    purchase_order_item_id = Column(Integer, ForeignKey("purchase_order_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity_received = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(14, 4), nullable=False)

    receipt = relationship("GoodsReceipt", back_populates="items")
    product = relationship("Product", lazy="selectin")
