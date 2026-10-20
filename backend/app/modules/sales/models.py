from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, VersionMixin


class SalesOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_SHIPPED = "PARTIALLY_SHIPPED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class SalesOrder(Base, TimestampMixin, VersionMixin):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)

    status = Column(String(30), default=SalesOrderStatus.DRAFT.value, nullable=False, index=True)

    subtotal = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    tax_total = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    total_amount = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)

    notes = Column(Text, nullable=True)
    confirmed_by = Column(Integer, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)

    customer = relationship("Customer", back_populates="sales_orders", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan", lazy="selectin")
    reservations = relationship("StockReservation", back_populates="sales_order", cascade="all, delete-orphan", lazy="selectin")
    shipments = relationship("Shipment", back_populates="sales_order", lazy="selectin")


class SalesOrderItem(Base, TimestampMixin):
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    shipped_quantity = Column(Integer, default=0, nullable=False)

    unit_price = Column(Numeric(14, 4), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    line_total = Column(Numeric(14, 4), nullable=False)

    sales_order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product", lazy="selectin")


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shipment_number = Column(String(50), unique=True, index=True, nullable=False)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)

    tracking_number = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)
    shipped_by = Column(Integer, nullable=True)

    sales_order = relationship("SalesOrder", back_populates="shipments")
    warehouse = relationship("Warehouse", lazy="selectin")
    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan", lazy="selectin")


class ShipmentItem(Base, TimestampMixin):
    __tablename__ = "shipment_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    sales_order_item_id = Column(Integer, ForeignKey("sales_order_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity_shipped = Column(Integer, nullable=False)

    shipment = relationship("Shipment", back_populates="items")
    product = relationship("Product", lazy="selectin")
