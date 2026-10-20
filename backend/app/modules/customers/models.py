from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    tax_identifier = Column(String(100), nullable=True)
    payment_terms = Column(String(100), default="NET30", nullable=False)

    billing_address = Column(Text, nullable=True)
    shipping_address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    sales_orders = relationship("SalesOrder", back_populates="customer")
