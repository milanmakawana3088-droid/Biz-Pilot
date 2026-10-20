from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PageParams, PaginatedResponse
from app.common.schemas import APIResponse
from app.core.permissions import Permission
from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_user,
    require_permissions,
    verify_warehouse_access,
)
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.sales.schemas import (
    SalesOrderCreate,
    SalesOrderResponse,
    ShipmentCreate,
    ShipmentResponse,
)
from app.modules.sales.service import SalesService

router = APIRouter(prefix="/sales-orders", tags=["Sales Orders & Dispatch"])


@router.get("", response_model=APIResponse[PaginatedResponse[SalesOrderResponse]])
async def list_sales_orders(
    warehouse_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    orders, total = await SalesService.list_sales_orders(
        session=session,
        warehouse_id=warehouse_id,
        customer_id=customer_id,
        status=status,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(orders, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.get("/{so_id}", response_model=APIResponse[SalesOrderResponse])
async def get_sales_order(
    so_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    so = await SalesService.get_by_id(session, so_id)
    verify_warehouse_access(current_user, so.warehouse_id)
    return APIResponse(success=True, data=so)


@router.post("", response_model=APIResponse[SalesOrderResponse], status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    data: SalesOrderCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.SO_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    verify_warehouse_access(current_user, data.warehouse_id)
    so = await SalesService.create_sales_order(
        session=session,
        data=data,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Sales order created in DRAFT status", data=so)


@router.post("/{so_id}/confirm", response_model=APIResponse[SalesOrderResponse])
async def confirm_sales_order(
    so_id: int,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.SO_CONFIRM)),
    session: AsyncSession = Depends(get_db),
):
    so = await SalesService.get_by_id(session, so_id)
    verify_warehouse_access(current_user, so.warehouse_id)

    confirmed = await SalesService.confirm_sales_order(
        session=session,
        so_id=so_id,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Sales order confirmed and stock reserved", data=confirmed)


@router.post("/{so_id}/ship", response_model=APIResponse[ShipmentResponse])
async def ship_sales_order(
    so_id: int,
    data: ShipmentCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.SO_SHIP)),
    session: AsyncSession = Depends(get_db),
):
    so = await SalesService.get_by_id(session, so_id)
    verify_warehouse_access(current_user, so.warehouse_id)

    shipment = await SalesService.ship_sales_order(
        session=session,
        so_id=so_id,
        data=data,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Shipment posted and stock deducted", data=shipment)


@router.post("/{so_id}/cancel", response_model=APIResponse[SalesOrderResponse])
async def cancel_sales_order(
    so_id: int,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.SO_CANCEL)),
    session: AsyncSession = Depends(get_db),
):
    so = await SalesService.get_by_id(session, so_id)
    verify_warehouse_access(current_user, so.warehouse_id)

    cancelled = await SalesService.cancel_sales_order(
        session=session,
        so_id=so_id,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Sales order cancelled and reservations released", data=cancelled)
