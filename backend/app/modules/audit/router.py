from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PageParams, PaginatedResponse
from app.common.schemas import APIResponse
from app.core.permissions import Permission
from app.db.session import get_db
from app.modules.auth.dependencies import require_permissions
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get("/logs", response_model=APIResponse[PaginatedResponse[AuditLogResponse]])
async def list_audit_logs(
    entity_name: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.AUDIT_READ)),
    session: AsyncSession = Depends(get_db),
):
    logs, total = await AuditService.list_audit_logs(
        session=session,
        page=page,
        size=size,
        entity_name=entity_name,
        action=action,
    )
    paginated = PaginatedResponse.create(logs, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)
