from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEntityException, EntityNotFoundException
from app.modules.locations.models import Location, Warehouse
from app.modules.locations.schemas import LocationCreate, WarehouseCreate


class LocationService:
    @staticmethod
    async def list_locations(session: AsyncSession) -> List[Location]:
        stmt = select(Location).order_by(Location.code.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_location(session: AsyncSession, data: LocationCreate) -> Location:
        stmt = select(Location).where(Location.code == data.code.upper().strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise DuplicateEntityException("Location", "code", data.code)

        loc = Location(
            code=data.code.upper().strip(),
            name=data.name.strip(),
            address=data.address,
            city=data.city,
            country=data.country,
            is_active=data.is_active,
        )
        session.add(loc)
        await session.commit()
        await session.refresh(loc)
        return loc

    @staticmethod
    async def list_warehouses(session: AsyncSession) -> List[Warehouse]:
        stmt = select(Warehouse).order_by(Warehouse.code.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_warehouse_by_id(session: AsyncSession, warehouse_id: int) -> Warehouse:
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        result = await session.execute(stmt)
        wh = result.scalar_one_or_none()
        if not wh:
            raise EntityNotFoundException("Warehouse", warehouse_id)
        return wh

    @staticmethod
    async def create_warehouse(session: AsyncSession, data: WarehouseCreate) -> Warehouse:
        # Check location exists
        loc_stmt = select(Location).where(Location.id == data.location_id)
        loc_res = await session.execute(loc_stmt)
        if not loc_res.scalar_one_or_none():
            raise EntityNotFoundException("Location", data.location_id)

        # Check code unique
        stmt = select(Warehouse).where(Warehouse.code == data.code.upper().strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise DuplicateEntityException("Warehouse", "code", data.code)

        wh = Warehouse(
            location_id=data.location_id,
            code=data.code.upper().strip(),
            name=data.name.strip(),
            is_active=data.is_active,
        )
        session.add(wh)
        await session.commit()
        await session.refresh(wh)
        return wh
