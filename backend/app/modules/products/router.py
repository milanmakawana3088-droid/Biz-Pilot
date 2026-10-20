from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PageParams, PaginatedResponse
from app.common.schemas import APIResponse
from app.core.permissions import Permission
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_permissions
from app.modules.auth.schemas import CurrentUserResponse
from app.modules.products.schemas import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    UnitOfMeasureCreate,
    UnitOfMeasureResponse,
)
from app.modules.products.service import ProductService

router = APIRouter(prefix="", tags=["Products & Master Data"])


# Categories
@router.get("/categories", response_model=APIResponse[List[ProductCategoryResponse]])
async def list_categories(
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    categories = await ProductService.list_categories(session)
    return APIResponse(success=True, data=categories)


@router.post("/categories", response_model=APIResponse[ProductCategoryResponse], status_code=status.HTTP_201_CREATED)
async def create_category(
    data: ProductCategoryCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PRODUCT_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    cat = await ProductService.create_category(session, data)
    return APIResponse(success=True, message="Category created", data=cat)


# Units of Measure
@router.get("/units-of-measure", response_model=APIResponse[List[UnitOfMeasureResponse]])
async def list_uoms(
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    uoms = await ProductService.list_uoms(session)
    return APIResponse(success=True, data=uoms)


@router.post("/units-of-measure", response_model=APIResponse[UnitOfMeasureResponse], status_code=status.HTTP_201_CREATED)
async def create_uom(
    data: UnitOfMeasureCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PRODUCT_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    uom = await ProductService.create_uom(session, data)
    return APIResponse(success=True, message="Unit of measure created", data=uom)


# Products
@router.get("/products", response_model=APIResponse[PaginatedResponse[ProductResponse]])
async def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    products, total = await ProductService.list_products(
        session,
        page=page,
        size=size,
        search=search,
        category_id=category_id,
        is_active=is_active,
    )
    paginated = PaginatedResponse.create(products, total, PageParams(page=page, size=size))
    return APIResponse(success=True, data=paginated)


@router.get("/products/{product_id}", response_model=APIResponse[ProductResponse])
async def get_product(
    product_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    product = await ProductService.get_by_id(session, product_id)
    return APIResponse(success=True, data=product)


@router.post("/products", response_model=APIResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PRODUCT_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    product = await ProductService.create_product(session, data, user_id=current_user.id)
    return APIResponse(success=True, message="Product created successfully", data=product)


@router.patch("/products/{product_id}", response_model=APIResponse[ProductResponse])
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PRODUCT_WRITE)),
    session: AsyncSession = Depends(get_db),
):
    product = await ProductService.update_product(session, product_id, data, user_id=current_user.id)
    return APIResponse(success=True, message="Product updated successfully", data=product)


@router.delete("/products/{product_id}", response_model=APIResponse[None])
async def delete_product(
    product_id: int,
    current_user: CurrentUserResponse = Depends(require_permissions(Permission.PRODUCT_DELETE)),
    session: AsyncSession = Depends(get_db),
):
    await ProductService.delete_product(session, product_id)
    return APIResponse(success=True, message="Product deleted or deactivated if referenced", data=None)
