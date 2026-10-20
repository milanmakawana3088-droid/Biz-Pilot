from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class SupplierBase(BaseModel):
    code: str
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tax_identifier: Optional[str] = None
    payment_terms: str = "NET30"
    address: Optional[str] = None
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tax_identifier: Optional[str] = None
    payment_terms: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
