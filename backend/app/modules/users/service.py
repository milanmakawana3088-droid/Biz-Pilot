from typing import List, Optional, Tuple
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEntityException, EntityNotFoundException
from app.core.security import hash_password
from app.modules.users.models import User, UserWarehouseAccess
from app.modules.users.schemas import UserCreate, UserUpdate


class UserService:
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise EntityNotFoundException("User", user_id)
        return user

    @staticmethod
    async def list_users(
        session: AsyncSession,
        page: int = 1,
        size: int = 50,
        search: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        query = select(User)
        count_query = select(func.count(User.id))

        if search:
            search_filter = (
                User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(User.id.asc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def create_user(session: AsyncSession, data: UserCreate) -> User:
        stmt = select(User).where(User.email == data.email.lower().strip())
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise DuplicateEntityException("User", "email", data.email)

        user = User(
            email=data.email.lower().strip(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            is_active=data.is_active,
        )
        session.add(user)
        await session.flush()

        for wid in data.warehouse_ids:
            access = UserWarehouseAccess(user_id=user.id, warehouse_id=wid)
            session.add(access)

        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
        user = await UserService.get_by_id(session, user_id)

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.password:
            user.hashed_password = hash_password(data.password)

        if data.warehouse_ids is not None:
            # Replace warehouse access assignments
            del_stmt = delete(UserWarehouseAccess).where(UserWarehouseAccess.user_id == user.id)
            await session.execute(del_stmt)
            for wid in data.warehouse_ids:
                session.add(UserWarehouseAccess(user_id=user.id, warehouse_id=wid))

        await session.commit()
        await session.refresh(user)
        return user
