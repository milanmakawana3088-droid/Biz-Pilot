from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import APIResponse
from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    user, warehouse_ids = await AuthService.authenticate_user(
        session=session,
        email=req.email,
        password=req.password,
    )
    access_token = create_access_token(user.id, user.role, warehouse_ids)
    refresh_token = create_refresh_token(user.id)
    permissions = AuthService.get_permissions_for_role(user.role)

    user_data = CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        warehouse_ids=warehouse_ids,
        permissions=permissions,
    )

    return APIResponse(
        success=True,
        message="Login successful",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_data,
        ),
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    req: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    user, access_token, new_refresh, warehouse_ids = await AuthService.refresh_tokens(
        session=session,
        refresh_token_str=req.refresh_token,
    )
    permissions = AuthService.get_permissions_for_role(user.role)

    user_data = CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        warehouse_ids=warehouse_ids,
        permissions=permissions,
    )

    return APIResponse(
        success=True,
        message="Token refreshed successfully",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            user=user_data,
        ),
    )


@router.get("/me", response_model=APIResponse[CurrentUserResponse])
async def get_me(
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    return APIResponse(
        success=True,
        message="Current user fetched",
        data=current_user,
    )


@router.post("/logout", response_model=APIResponse[None])
async def logout(
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    # JWT tokens are stateless, revocation can be tracked in Redis if needed.
    return APIResponse(
        success=True,
        message="Logout successful",
        data=None,
    )
