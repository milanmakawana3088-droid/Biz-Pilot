from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import APIResponse
from app.core.permissions import Permission
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_permissions
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.locations.schemas import (
    LocationCreate,
    LocationResponse,
    WarehouseCreate,
    WarehouseResponse,
)
from app.modules.locations.service import LocationService

router = APIRouter(prefix="", tags=["Locations & Warehouses"])


@router.get("/locations", response_model=APIResponse[List[LocationResponse]])
async def list_locations(
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    locations = await LocationService.list_locations(session)
    return APIResponse(success=True, data=locations)


@router.post("/locations", response_model=APIResponse[LocationResponse], status_code=status.HTTP_201_CREATED)
async def create_location(
    data: LocationCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.WAREHOUSE_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    loc = await LocationService.create_location(session, data)
    return APIResponse(success=True, message="Location created", data=loc)


@router.get("/warehouses", response_model=APIResponse[List[WarehouseResponse]])
async def list_warehouses(
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    warehouses = await LocationService.list_warehouses(session)
    # If not admin, can still view warehouse list or filter by assigned
    return APIResponse(success=True, data=warehouses)


@router.post("/warehouses", response_model=APIResponse[WarehouseResponse], status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    data: WarehouseCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.WAREHOUSE_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    wh = await LocationService.create_warehouse(session, data)
    return APIResponse(success=True, message="Warehouse created", data=wh)
