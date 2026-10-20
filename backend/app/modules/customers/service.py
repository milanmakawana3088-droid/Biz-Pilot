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
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate, CustomerResponse, CustomerUpdate


class CustomerService:
    @staticmethod
    async def list_customers(
        session: AsyncSession,
        page: int = 1,
        size: int = 50,
        search: Optional[str] = None,
    ) -> Tuple[List[Customer], int]:
        query = select(Customer)
        count_query = select(func.count(Customer.id))

        if search:
            filt = Customer.name.ilike(f"%{search}%") | Customer.code.ilike(f"%{search}%")
            query = query.where(filt)
            count_query = count_query.where(filt)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Customer.name.asc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_by_id(session: AsyncSession, customer_id: int) -> Customer:
        stmt = select(Customer).where(Customer.id == customer_id)
        result = await session.execute(stmt)
        cust = result.scalar_one_or_none()
        if not cust:
            raise EntityNotFoundException("Customer", customer_id)
        return cust

    @staticmethod
    async def create_customer(session: AsyncSession, data: CustomerCreate) -> Customer:
        stmt = select(Customer).where(Customer.code == data.code.upper().strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise DuplicateEntityException("Customer", "code", data.code)

        cust = Customer(
            code=data.code.upper().strip(),
            name=data.name.strip(),
            email=str(data.email) if data.email else None,
            phone=data.phone,
            tax_identifier=data.tax_identifier,
            payment_terms=data.payment_terms,
            billing_address=data.billing_address,
            shipping_address=data.shipping_address,
            is_active=data.is_active,
        )
        session.add(cust)
        await session.commit()
        await session.refresh(cust)
        return cust

    @staticmethod
    async def update_customer(session: AsyncSession, customer_id: int, data: CustomerUpdate) -> Customer:
        cust = await CustomerService.get_by_id(session, customer_id)
        if data.name is not None:
            cust.name = data.name.strip()
        if data.email is not None:
            cust.email = str(data.email)
        if data.phone is not None:
            cust.phone = data.phone
        if data.tax_identifier is not None:
            cust.tax_identifier = data.tax_identifier
        if data.payment_terms is not None:
            cust.payment_terms = data.payment_terms
        if data.billing_address is not None:
            cust.billing_address = data.billing_address
        if data.shipping_address is not None:
            cust.shipping_address = data.shipping_address
        if data.is_active is not None:
            cust.is_active = data.is_active

        await session.commit()
        await session.refresh(cust)
        return cust


router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=APIResponse[PaginatedResponse[CustomerResponse]])
async def list_customers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    customers, total = await CustomerService.list_customers(session, page=page, size=size, search=search)
    paginated = PaginatedResponse.create(customers, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.get("/{customer_id}", response_model=APIResponse[CustomerResponse])
async def get_customer(
    customer_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    cust = await CustomerService.get_by_id(session, customer_id)
    return APIResponse(success=True, data=cust)


@router.post("", response_model=APIResponse[CustomerResponse], status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.CUSTOMER_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    cust = await CustomerService.create_customer(session, data)
    return APIResponse(success=True, message="Customer created successfully", data=cust)


@router.patch("/{customer_id}", response_model=APIResponse[CustomerResponse])
async def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.CUSTOMER_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    cust = await CustomerService.update_customer(session, customer_id, data)
    return APIResponse(success=True, message="Customer updated successfully", data=cust)
