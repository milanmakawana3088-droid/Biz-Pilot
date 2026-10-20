from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.customers.models import Customer
from app.modules.inventory.models import StockLevel
from app.modules.locations.models import Warehouse
from app.modules.products.models import Product, ProductCategory
from app.modules.purchasing.models import PurchaseOrder, PurchaseOrderStatus
from app.modules.reporting.schemas import (
    DashboardMetricsResponse,
    LowStockAlert,
    WarehouseValuation,
)
from app.modules.sales.models import SalesOrder, SalesOrderStatus
from app.modules.suppliers.models import Supplier


class ReportingService:
    @staticmethod
    async def get_dashboard_metrics(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        # Total counts
        total_products = (await session.execute(select(func.count(Product.id)))).scalar() or 0
        total_warehouses = (await session.execute(select(func.count(Warehouse.id)))).scalar() or 0
        total_customers = (await session.execute(select(func.count(Customer.id)))).scalar() or 0
        total_suppliers = (await session.execute(select(func.count(Supplier.id)))).scalar() or 0

        # Stock totals query
        stock_query = select(
            func.coalesce(func.sum(StockLevel.on_hand), 0),
            func.coalesce(func.sum(StockLevel.reserved), 0),
            func.coalesce(func.sum(StockLevel.on_hand * Product.cost_price), Decimal("0.00")),
        ).join(StockLevel.product)

        if warehouse_id:
            stock_query = stock_query.where(StockLevel.warehouse_id == warehouse_id)

        stock_agg = await session.execute(stock_query)
        agg_row = stock_agg.one()
        total_on_hand = int(agg_row[0])
        total_reserved = int(agg_row[1])
        total_valuation = float(Decimal(str(agg_row[2])))

        # Low stock count query
        low_stock_query = (
            select(func.count(StockLevel.id))
            .join(StockLevel.product)
            .where((StockLevel.on_hand - StockLevel.reserved) <= Product.reorder_level)
        )
        if warehouse_id:
            low_stock_query = low_stock_query.where(StockLevel.warehouse_id == warehouse_id)

        low_stock_res = await session.execute(low_stock_query)
        low_stock_count = low_stock_res.scalar() or 0

        # Open orders query
        open_po_query = select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.DRAFT.value,
                PurchaseOrderStatus.APPROVED.value,
                PurchaseOrderStatus.PARTIALLY_RECEIVED.value,
            ])
        )
        if warehouse_id:
            open_po_query = open_po_query.where(PurchaseOrder.warehouse_id == warehouse_id)

        open_pos = (await session.execute(open_po_query)).scalar() or 0

        open_so_query = select(func.count(SalesOrder.id)).where(
            SalesOrder.status.in_([
                SalesOrderStatus.DRAFT.value,
                SalesOrderStatus.CONFIRMED.value,
                SalesOrderStatus.PARTIALLY_SHIPPED.value,
            ])
        )
        if warehouse_id:
            open_so_query = open_so_query.where(SalesOrder.warehouse_id == warehouse_id)

        open_sos = (await session.execute(open_so_query)).scalar() or 0

        # Warehouse breakdown
        wh_stmt = select(Warehouse).order_by(Warehouse.name.asc())
        wh_res = await session.execute(wh_stmt)
        warehouses = wh_res.scalars().all()

        breakdown: List[Dict[str, Any]] = []
        for wh in warehouses:
            wh_agg = await session.execute(
                select(
                    func.count(StockLevel.id),
                    func.coalesce(func.sum(StockLevel.on_hand), 0),
                    func.coalesce(func.sum(StockLevel.reserved), 0),
                    func.coalesce(func.sum(StockLevel.on_hand * Product.cost_price), Decimal("0.00")),
                )
                .join(StockLevel.product)
                .where(StockLevel.warehouse_id == wh.id)
            )
            wh_row = wh_agg.one()
            breakdown.append({
                "warehouse_id": wh.id,
                "warehouse_code": wh.code,
                "warehouse_name": wh.name,
                "total_items": int(wh_row[0]),
                "total_on_hand": int(wh_row[1]),
                "total_reserved": int(wh_row[2]),
                "total_valuation": float(Decimal(str(wh_row[3]))),
            })

        return {
            "total_products": total_products,
            "total_warehouses": total_warehouses,
            "total_customers": total_customers,
            "total_suppliers": total_suppliers,
            "total_on_hand_units": total_on_hand,
            "total_reserved_units": total_reserved,
            "low_stock_count": low_stock_count,
            "low_stock_alerts_count": low_stock_count,
            "total_valuation": total_valuation,
            "total_inventory_valuation": total_valuation,
            "open_pos_count": open_pos,
            "total_open_purchase_orders": open_pos,
            "open_sos_count": open_sos,
            "total_open_sales_orders": open_sos,
            "warehouse_breakdown": breakdown,
        }

    @staticmethod
    async def get_valuation_report(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(StockLevel)
            .options(selectinload(StockLevel.product), selectinload(StockLevel.warehouse))
        )
        if warehouse_id:
            stmt = stmt.where(StockLevel.warehouse_id == warehouse_id)

        res = await session.execute(stmt)
        levels = res.scalars().all()

        result = []
        for sl in levels:
            cost = float(sl.product.cost_price) if sl.product else 0.0
            result.append({
                "product_id": str(sl.product_id),
                "sku": sl.product.sku if sl.product else f"SKU-{sl.product_id}",
                "product_name": sl.product.name if sl.product else f"Product #{sl.product_id}",
                "warehouse_id": str(sl.warehouse_id),
                "warehouse_name": sl.warehouse.name if sl.warehouse else f"Warehouse #{sl.warehouse_id}",
                "on_hand": sl.on_hand,
                "reserved": sl.reserved,
                "available": sl.available,
                "unit_cost": cost,
                "total_valuation": round(sl.on_hand * cost, 2),
            })
        return result

    @staticmethod
    async def get_replenishment_report(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(StockLevel)
            .join(StockLevel.product)
            .options(selectinload(StockLevel.product), selectinload(StockLevel.warehouse))
            .where((StockLevel.on_hand - StockLevel.reserved) <= Product.reorder_level)
        )
        if warehouse_id:
            stmt = stmt.where(StockLevel.warehouse_id == warehouse_id)

        res = await session.execute(stmt)
        levels = res.scalars().all()

        result = []
        for sl in levels:
            reorder_pt = sl.product.reorder_level if sl.product else 10
            shortage = max(0, reorder_pt - sl.available)
            suggested = shortage + 20
            result.append({
                "product_id": str(sl.product_id),
                "sku": sl.product.sku if sl.product else f"SKU-{sl.product_id}",
                "product_name": sl.product.name if sl.product else f"Product #{sl.product_id}",
                "warehouse_id": str(sl.warehouse_id),
                "warehouse_name": sl.warehouse.name if sl.warehouse else f"Warehouse #{sl.warehouse_id}",
                "on_hand": sl.on_hand,
                "reserved": sl.reserved,
                "available": sl.available,
                "reorder_point": reorder_pt,
                "safety_stock": 5,
                "shortage_quantity": shortage,
                "suggested_order_quantity": suggested,
            })
        return result

    @staticmethod
    async def get_low_stock_alerts(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[LowStockAlert]:
        query = (
            select(
                Product.id.label("product_id"),
                Product.sku,
                Product.name,
                ProductCategory.name.label("category_name"),
                Warehouse.id.label("warehouse_id"),
                Warehouse.code.label("warehouse_code"),
                StockLevel.on_hand,
                Product.reorder_level,
                (Product.reorder_level - StockLevel.on_hand).label("deficit"),
            )
            .join(StockLevel, StockLevel.product_id == Product.id)
            .join(Warehouse, Warehouse.id == StockLevel.warehouse_id)
            .outerjoin(ProductCategory, ProductCategory.id == Product.category_id)
            .where(StockLevel.on_hand <= Product.reorder_level)
        )

        if warehouse_id:
            query = query.where(StockLevel.warehouse_id == warehouse_id)

        query = query.order_by((Product.reorder_level - StockLevel.on_hand).desc()).limit(limit)
        result = await session.execute(query)
        rows = result.all()

        alerts = [
            LowStockAlert(
                product_id=r.product_id,
                sku=r.sku,
                name=r.name,
                category_name=r.category_name,
                warehouse_id=r.warehouse_id,
                warehouse_code=r.warehouse_code,
                on_hand=r.on_hand,
                reorder_level=r.reorder_level,
                deficit=max(0, r.deficit),
            )
            for r in rows
        ]
        return alerts
