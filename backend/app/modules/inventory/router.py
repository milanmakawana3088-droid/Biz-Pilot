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
from app.modules.inventory.schemas import (
    StockAdjustmentRequest,
    StockLevelResponse,
    StockMovementResponse,
    TransferCreateRequest,
    TransferResponse,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory & Stock Engine"])


@router.get("/stock-levels", response_model=APIResponse[PaginatedResponse[StockLevelResponse]])
async def list_stock_levels(
    warehouse_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    low_stock_only: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    levels, total = await InventoryService.list_stock_levels(
        session=session,
        warehouse_id=warehouse_id,
        product_id=product_id,
        low_stock_only=low_stock_only,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(levels, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.get("/movements", response_model=APIResponse[PaginatedResponse[StockMovementResponse]])
async def list_movements(
    warehouse_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    movements, total = await InventoryService.list_movements(
        session=session,
        warehouse_id=warehouse_id,
        product_id=product_id,
        movement_type=movement_type,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(movements, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.post("/adjustments", response_model=APIResponse[StockLevelResponse], status_code=status.HTTP_201_CREATED)
async def adjust_stock(
    req: StockAdjustmentRequest,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.STOCK_ADJUST)),
    session: AsyncSession = Depends(get_db),
):
    verify_warehouse_access(current_user, req.warehouse_id)

    stock = await InventoryService.adjust_stock(
        session=session,
        req=req,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    return APIResponse(success=True, message="Stock adjusted successfully", data=stock)


@router.post("/transfers", response_model=APIResponse[TransferResponse], status_code=status.HTTP_201_CREATED)
async def create_transfer(
    req: TransferCreateRequest,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.STOCK_TRANSFER)),
    session: AsyncSession = Depends(get_db),
):
    verify_warehouse_access(current_user, req.source_warehouse_id)

    transfer = await InventoryService.create_and_execute_transfer(
        session=session,
        req=req,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    return APIResponse(success=True, message="Stock transferred successfully", data=transfer)
