from decimal import Decimal
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, VersionMixin


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    products = relationship("Product", back_populates="category")


class UnitOfMeasure(Base, TimestampMixin):
    __tablename__ = "units_of_measure"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(20), unique=True, index=True, nullable=False)  # e.g. 'PCS', 'KG', 'BOX'
    name = Column(String(100), nullable=False)

    products = relationship("Product", back_populates="uom")


class Product(Base, TimestampMixin, VersionMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    uom_id = Column(Integer, ForeignKey("units_of_measure.id", ondelete="RESTRICT"), nullable=False, index=True)

    cost_price = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    selling_price = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    tax_rate = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)  # Percentage, e.g. 5.00 for 5%

    reorder_level = Column(Integer, default=10, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)

    category = relationship("ProductCategory", back_populates="products", lazy="selectin")
    uom = relationship("UnitOfMeasure", back_populates="products", lazy="selectin")
    stock_levels = relationship("StockLevel", back_populates="product")
