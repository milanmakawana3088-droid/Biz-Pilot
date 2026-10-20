from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="VIEWER", nullable=False)  # RoleEnum
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    warehouse_accesses = relationship(
        "UserWarehouseAccess",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserWarehouseAccess(Base, TimestampMixin):
    __tablename__ = "user_warehouse_access"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)

    user = relationship("User", back_populates="warehouse_accesses")
    warehouse = relationship("Warehouse", back_populates="user_accesses")

    __table_args__ = (
        UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse"),
    )
