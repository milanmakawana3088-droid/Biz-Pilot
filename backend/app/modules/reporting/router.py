from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import APIResponse
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, verify_warehouse_access
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.reporting.schemas import LowStockAlert
from app.modules.reporting.service import ReportingService

router = APIRouter(prefix="", tags=["Reporting & Analytics"])


@router.get("/dashboard", response_model=APIResponse[Dict[str, Any]])
async def get_dashboard_metrics(
    warehouse_id: Optional[int] = Query(None),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    metrics = await ReportingService.get_dashboard_metrics(session, warehouse_id=warehouse_id)
    return APIResponse(success=True, data=metrics)


@router.get("/valuation", response_model=APIResponse[List[Dict[str, Any]]])
async def get_valuation_report(
    warehouse_id: Optional[int] = Query(None),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    valuation = await ReportingService.get_valuation_report(session, warehouse_id=warehouse_id)
    return APIResponse(success=True, data=valuation)


@router.get("/replenishment", response_model=APIResponse[List[Dict[str, Any]]])
async def get_replenishment_report(
    warehouse_id: Optional[int] = Query(None),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    replenishment = await ReportingService.get_replenishment_report(session, warehouse_id=warehouse_id)
    return APIResponse(success=True, data=replenishment)


@router.get("/low-stock-alerts", response_model=APIResponse[List[LowStockAlert]])
async def get_low_stock_alerts(
    warehouse_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if warehouse_id:
        verify_warehouse_access(current_user, warehouse_id)

    alerts = await ReportingService.get_low_stock_alerts(session, warehouse_id=warehouse_id, limit=limit)
    return APIResponse(success=True, data=alerts)
