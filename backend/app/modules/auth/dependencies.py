from typing import Callable, List
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthenticationFailedException,
    PermissionDeniedException,
    UnauthorizedWarehouseAccessException,
)
from app.core.permissions import Permission, RoleEnum
from app.core.security import decode_token
from app.db.session import get_db
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.auth.service import AuthService
from app.modules.users.models import User

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: AsyncSession = Depends(get_db),
) -> CurrentUserResponse:
    if not credentials:
        raise AuthenticationFailedException("Authentication token required.")

    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise AuthenticationFailedException("Access token required.")
        user_id = int(payload.get("sub"))
    except Exception as e:
        raise AuthenticationFailedException(f"Invalid access token: {str(e)}")

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationFailedException("User not found or account is deactivated.")

    warehouse_ids = await AuthService.get_user_warehouse_ids(session, user.id)
    permissions = AuthService.get_permissions_for_role(user.role)

    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        warehouse_ids=warehouse_ids,
        permissions=permissions,
    )


def require_permissions(*required_permissions: Permission) -> Callable:
    async def permission_checker(
        current_user: CurrentUserResponse = Depends(get_current_user),
    ) -> CurrentUserResponse:
        # Superuser / ADMIN role has automatic access
        if current_user.role == RoleEnum.ADMIN.value or current_user.is_superuser:
            return current_user

        user_perms = set(current_user.permissions)
        for req in required_permissions:
            if req.value not in user_perms:
                raise PermissionDeniedException(req.value)

        return current_user

    return permission_checker


def verify_warehouse_access(
    current_user: CurrentUserResponse,
    warehouse_id: int,
) -> None:
    """
    Critical authorization rule:
    Every stock-affecting operation must verify that the user is explicitly authorized
    for the target warehouse (unless user is ADMIN).
    """
    if current_user.role == RoleEnum.ADMIN.value or current_user.is_superuser:
        return

    if warehouse_id not in current_user.warehouse_ids:
        raise UnauthorizedWarehouseAccessException(
            user_id=current_user.id,
            warehouse_id=warehouse_id,
        )
