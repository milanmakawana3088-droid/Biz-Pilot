from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PageParams, PaginatedResponse
from app.common.schemas import APIResponse
from app.core.permissions import Permission
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_permissions
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.auth.service import AuthService
from app.modules.users.schemas import UserCreate, UserResponse, UserUpdate
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=APIResponse[PaginatedResponse[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.USER_READ)),
    session: AsyncSession = Depends(get_db),
):
    users, total = await UserService.list_users(session, page=page, size=size, search=search)
    user_responses = []
    for u in users:
        wids = await AuthService.get_user_warehouse_ids(session, u.id)
        user_responses.append(
            UserResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                warehouse_ids=wids,
                created_at=u.created_at,
            )
        )
    paginated = PaginatedResponse.create(user_responses, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.post("", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.USER_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    user = await UserService.create_user(session, data)
    wids = await AuthService.get_user_warehouse_ids(session, user.id)
    return APIResponse(
        success=True,
        message="User created successfully",
        data=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            warehouse_ids=wids,
            created_at=user.created_at,
        ),
    )


@router.patch("/{user_id}", response_model=APIResponse[UserResponse])
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.USER_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    user = await UserService.update_user(session, user_id, data)
    wids = await AuthService.get_user_warehouse_ids(session, user.id)
    return APIResponse(
        success=True,
        message="User updated successfully",
        data=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            warehouse_ids=wids,
            created_at=user.created_at,
        ),
    )
