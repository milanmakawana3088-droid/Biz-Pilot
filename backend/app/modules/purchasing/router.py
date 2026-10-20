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
from app.modules.purchasing.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
)
from app.modules.purchasing.service import PurchasingService

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders & Receiving"])


@router.get("", response_model=APIResponse[PaginatedResponse[PurchaseOrderResponse]])
async def list_purchase_orders(
    warehouse_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    orders, total = await PurchasingService.list_purchase_orders(
        session=session,
        warehouse_id=warehouse_id,
        supplier_id=supplier_id,
        status=status,
        page=page,
        size=size,
    )
    paginated = PaginatedResponse.create(orders, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.get("/{po_id}", response_model=APIResponse[PurchaseOrderResponse])
async def get_purchase_order(
    po_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    po = await PurchasingService.get_by_id(session, po_id)
    verify_warehouse_access(current_user, po.warehouse_id)
    return APIResponse(success=True, data=po)


@router.post("", response_model=APIResponse[PurchaseOrderResponse], status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: PurchaseOrderCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PO_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    verify_warehouse_access(current_user, data.warehouse_id)
    po = await PurchasingService.create_purchase_order(
        session=session,
        data=data,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Purchase order created in DRAFT status", data=po)


@router.post("/{po_id}/approve", response_model=APIResponse[PurchaseOrderResponse])
async def approve_purchase_order(
    po_id: int,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PO_APPROVE)),
    session: AsyncSession = Depends(get_db),
):
    po = await PurchasingService.get_by_id(session, po_id)
    verify_warehouse_access(current_user, po.warehouse_id)

    approved = await PurchasingService.approve_purchase_order(
        session=session,
        po_id=po_id,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Purchase order approved", data=approved)


@router.post("/{po_id}/receive", response_model=APIResponse[GoodsReceiptResponse])
async def receive_goods(
    po_id: int,
    data: GoodsReceiptCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PO_RECEIVE)),
    session: AsyncSession = Depends(get_db),
):
    po = await PurchasingService.get_by_id(session, po_id)
    verify_warehouse_access(current_user, po.warehouse_id)

    receipt = await PurchasingService.receive_goods(
        session=session,
        po_id=po_id,
        data=data,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Goods received and stock balances updated", data=receipt)


@router.post("/{po_id}/cancel", response_model=APIResponse[PurchaseOrderResponse])
async def cancel_purchase_order(
    po_id: int,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PO_CANCEL)),
    session: AsyncSession = Depends(get_db),
):
    po = await PurchasingService.get_by_id(session, po_id)
    verify_warehouse_access(current_user, po.warehouse_id)

    cancelled = await PurchasingService.cancel_purchase_order(
        session=session,
        po_id=po_id,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return APIResponse(success=True, message="Purchase order cancelled", data=cancelled)
