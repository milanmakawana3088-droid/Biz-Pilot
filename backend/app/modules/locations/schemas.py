from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class LocationBase(BaseModel):
    code: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_active: bool = True


class LocationCreate(LocationBase):
    pass


class LocationResponse(LocationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseBase(BaseModel):
    location_id: int
    code: str
    name: str
    is_active: bool = True


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseResponse(WarehouseBase):
    id: int
    location: Optional[LocationResponse] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
