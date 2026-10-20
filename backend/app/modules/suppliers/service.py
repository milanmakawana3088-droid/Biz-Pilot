from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PageParams, PaginatedResponse
from app.common.schemas import APIResponse
from app.core.exceptions import DuplicateEntityException, EntityNotFoundException
from app.core.permissions import Permission
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_permissions
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.schemas import SupplierCreate, SupplierResponse, SupplierUpdate


class SupplierService:
    @staticmethod
    async def list_suppliers(
        session: AsyncSession,
        page: int = 1,
        size: int = 50,
        search: Optional[str] = None,
    ) -> Tuple[List[Supplier], int]:
        query = select(Supplier)
        count_query = select(func.count(Supplier.id))

        if search:
            filt = Supplier.name.ilike(f"%{search}%") | Supplier.code.ilike(f"%{search}%")
            query = query.where(filt)
            count_query = count_query.where(filt)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Supplier.name.asc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_by_id(session: AsyncSession, supplier_id: int) -> Supplier:
        stmt = select(Supplier).where(Supplier.id == supplier_id)
        result = await session.execute(stmt)
        supp = result.scalar_one_or_none()
        if not supp:
            raise EntityNotFoundException("Supplier", supplier_id)
        return supp

    @staticmethod
    async def create_supplier(session: AsyncSession, data: SupplierCreate) -> Supplier:
        stmt = select(Supplier).where(Supplier.code == data.code.upper().strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise DuplicateEntityException("Supplier", "code", data.code)

        supp = Supplier(
            code=data.code.upper().strip(),
            name=data.name.strip(),
            email=str(data.email) if data.email else None,
            phone=data.phone,
            tax_identifier=data.tax_identifier,
            payment_terms=data.payment_terms,
            address=data.address,
            is_active=data.is_active,
        )
        session.add(supp)
        await session.commit()
        await session.refresh(supp)
        return supp

    @staticmethod
    async def update_supplier(session: AsyncSession, supplier_id: int, data: SupplierUpdate) -> Supplier:
        supp = await SupplierService.get_by_id(session, supplier_id)
        if data.name is not None:
            supp.name = data.name.strip()
        if data.email is not None:
            supp.email = str(data.email)
        if data.phone is not None:
            supp.phone = data.phone
        if data.tax_identifier is not None:
            supp.tax_identifier = data.tax_identifier
        if data.payment_terms is not None:
            supp.payment_terms = data.payment_terms
        if data.address is not None:
            supp.address = data.address
        if data.is_active is not None:
            supp.is_active = data.is_active

        await session.commit()
        await session.refresh(supp)
        return supp


router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=APIResponse[PaginatedResponse[SupplierResponse]])
async def list_suppliers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    suppliers, total = await SupplierService.list_suppliers(session, page=page, size=size, search=search)
    paginated = PaginatedResponse.create(suppliers, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.get("/{supplier_id}", response_model=APIResponse[SupplierResponse])
async def get_supplier(
    supplier_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    supp = await SupplierService.get_by_id(session, supplier_id)
    return APIResponse(success=True, data=supp)


@router.post("", response_model=APIResponse[SupplierResponse], status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.SUPPLIER_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    supp = await SupplierService.create_supplier(session, data)
    return APIResponse(success=True, message="Supplier created successfully", data=supp)


@router.patch("/{supplier_id}", response_model=APIResponse[SupplierResponse])
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.SUPPLIER_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    supp = await SupplierService.update_supplier(session, supplier_id, data)
    return APIResponse(success=True, message="Supplier updated successfully", data=supp)
