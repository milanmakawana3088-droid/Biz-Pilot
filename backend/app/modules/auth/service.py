from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationFailedException
from app.core.permissions import ROLE_PERMISSIONS_MAP, RoleEnum
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.users.models import User, UserWarehouseAccess


class AuthService:
    @staticmethod
    async def get_user_warehouse_ids(session: AsyncSession, user_id: int) -> List[int]:
        stmt = select(UserWarehouseAccess.warehouse_id).where(UserWarehouseAccess.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def authenticate_user(
        session: AsyncSession,
        email: str,
        password: str,
    ) -> Tuple[User, List[int]]:
        stmt = select(User).where(User.email == email.lower().strip())
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationFailedException("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationFailedException("User account is inactive.")

        warehouse_ids = await AuthService.get_user_warehouse_ids(session, user.id)
        return user, warehouse_ids

    @staticmethod
    def get_permissions_for_role(role_name: str) -> List[str]:
        try:
            role = RoleEnum(role_name)
            perms = ROLE_PERMISSIONS_MAP.get(role, set())
            return [p.value for p in perms]
        except ValueError:
            return []

    @staticmethod
    async def refresh_tokens(session: AsyncSession, refresh_token_str: str) -> Tuple[User, str, str, List[int]]:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise AuthenticationFailedException("Invalid token type.")
            user_id = int(payload.get("sub"))
        except Exception:
            raise AuthenticationFailedException("Invalid or expired refresh token.")

        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationFailedException("User no longer exists or is inactive.")

        warehouse_ids = await AuthService.get_user_warehouse_ids(session, user.id)
        new_access = create_access_token(user.id, user.role, warehouse_ids)
        new_refresh = create_refresh_token(user.id)
        return user, new_access, new_refresh, warehouse_ids

    @staticmethod
    async def seed_default_admin(session: AsyncSession) -> User:
        """Seed initial Admin user if database is freshly initialized."""
        stmt = select(User).where(User.email == "admin@bizpilot.io")
        result = await session.execute(stmt)
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                email="admin@bizpilot.io",
                hashed_password=hash_password("Admin123!"),
                full_name="System Administrator",
                role=RoleEnum.ADMIN.value,
                is_active=True,
                is_superuser=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
        return admin
