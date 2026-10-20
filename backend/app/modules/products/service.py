from typing import List, Optional, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppException,
    DuplicateEntityException,
    EntityNotFoundException,
)
from app.modules.inventory.models import StockMovement
from app.modules.products.models import Product, ProductCategory, UnitOfMeasure
from app.modules.products.schemas import (
    ProductCategoryCreate,
    ProductCreate,
    ProductUpdate,
    UnitOfMeasureCreate,
)


class ProductService:
    @staticmethod
    async def list_categories(session: AsyncSession) -> List[ProductCategory]:
        stmt = select(ProductCategory).order_by(ProductCategory.name.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_category(session: AsyncSession, data: ProductCategoryCreate) -> ProductCategory:
        stmt = select(ProductCategory).where(ProductCategory.code == data.code.upper().strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise DuplicateEntityException("ProductCategory", "code", data.code)
        cat = ProductCategory(
            code=data.code.upper().strip(),
            name=data.name.strip(),
            description=data.description,
        )
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat

    @staticmethod
    async def list_uoms(session: AsyncSession) -> List[UnitOfMeasure]:
        stmt = select(UnitOfMeasure).order_by(UnitOfMeasure.name.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_uom(session: AsyncSession, data: UnitOfMeasureCreate) -> UnitOfMeasure:
        stmt = select(UnitOfMeasure).where(UnitOfMeasure.code == data.code.upper().strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise DuplicateEntityException("UnitOfMeasure", "code", data.code)
        uom = UnitOfMeasure(
            code=data.code.upper().strip(),
            name=data.name.strip(),
        )
        session.add(uom)
        await session.commit()
        await session.refresh(uom)
        return uom

    @staticmethod
    async def list_products(
        session: AsyncSession,
        page: int = 1,
        size: int = 50,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Product], int]:
        query = select(Product)
        count_query = select(func.count(Product.id))

        if search:
            search_filt = (
                Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%")
            )
            query = query.where(search_filt)
            count_query = count_query.where(search_filt)

        if category_id:
            query = query.where(Product.category_id == category_id)
            count_query = count_query.where(Product.category_id == category_id)

        if is_active is not None:
            query = query.where(Product.is_active == is_active)
            count_query = count_query.where(Product.is_active == is_active)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Product.name.asc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_by_id(session: AsyncSession, product_id: int) -> Product:
        stmt = select(Product).where(Product.id == product_id)
        result = await session.execute(stmt)
        prod = result.scalar_one_or_none()
        if not prod:
            raise EntityNotFoundException("Product", product_id)
        return prod

    @staticmethod
    async def create_product(
        session: AsyncSession,
        data: ProductCreate,
        user_id: Optional[int] = None,
    ) -> Product:
        # Check SKU unique
        stmt = select(Product).where(Product.sku == data.sku.upper().strip())
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise DuplicateEntityException("Product", "sku", data.sku)

        # Check UOM exists
        uom_stmt = select(UnitOfMeasure).where(UnitOfMeasure.id == data.uom_id)
        uom_res = await session.execute(uom_stmt)
        if not uom_res.scalar_one_or_none():
            raise EntityNotFoundException("UnitOfMeasure", data.uom_id)

        prod = Product(
            sku=data.sku.upper().strip(),
            name=data.name.strip(),
            description=data.description,
            category_id=data.category_id,
            uom_id=data.uom_id,
            cost_price=data.cost_price,
            selling_price=data.selling_price,
            tax_rate=data.tax_rate,
            reorder_level=data.reorder_level,
            is_active=data.is_active,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(prod)
        await session.commit()
        await session.refresh(prod)
        return prod

    @staticmethod
    async def update_product(
        session: AsyncSession,
        product_id: int,
        data: ProductUpdate,
        user_id: Optional[int] = None,
    ) -> Product:
        prod = await ProductService.get_by_id(session, product_id)

        if data.name is not None:
            prod.name = data.name.strip()
        if data.description is not None:
            prod.description = data.description
        if data.category_id is not None:
            prod.category_id = data.category_id
        if data.uom_id is not None:
            prod.uom_id = data.uom_id
        if data.cost_price is not None:
            prod.cost_price = data.cost_price
        if data.selling_price is not None:
            prod.selling_price = data.selling_price
        if data.tax_rate is not None:
            prod.tax_rate = data.tax_rate
        if data.reorder_level is not None:
            prod.reorder_level = data.reorder_level
        if data.is_active is not None:
            prod.is_active = data.is_active

        prod.updated_by = user_id
        await session.commit()
        await session.refresh(prod)
        return prod

    @staticmethod
    async def delete_product(session: AsyncSession, product_id: int) -> None:
        """
        Soft-deactivate or delete if unreferenced.
        Do not physically delete products referenced by stock movements or historical orders.
        """
        prod = await ProductService.get_by_id(session, product_id)

        # Check for stock movements
        mov_stmt = select(func.count(StockMovement.id)).where(StockMovement.product_id == product_id)
        mov_res = await session.execute(mov_stmt)
        movement_count = mov_res.scalar() or 0

        if movement_count > 0:
            # Cannot physically delete: soft-deactivate instead
            prod.is_active = False
            await session.commit()
            return

        # If zero movements, safe to remove
        await session.delete(prod)
        await session.commit()
