from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession


from app.common.numbering import get_next_document_number
from app.core.exceptions import (
    AppException,
    EntityNotFoundException,
    InsufficientStockException,
    InvalidStateTransitionException,
)
from app.modules.audit.service import AuditService
from app.modules.customers.models import Customer
from app.modules.inventory.models import (
    MovementType,
    ReservationStatus,
    StockLevel,
    StockReservation,
)
from app.modules.inventory.service import InventoryService
from app.modules.locations.models import Warehouse
from app.modules.products.models import Product
from app.modules.sales.models import (
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatus,
    Shipment,
    ShipmentItem,
)
from app.modules.sales.schemas import SalesOrderCreate, ShipmentCreate


class SalesService:
    @staticmethod
    async def get_by_id(session: AsyncSession, so_id: int) -> SalesOrder:
        stmt = (
            select(SalesOrder)
            .where(SalesOrder.id == so_id)
            .options(
                selectinload(SalesOrder.customer),
                selectinload(SalesOrder.warehouse),
                selectinload(SalesOrder.items).selectinload(SalesOrderItem.product),
                selectinload(SalesOrder.shipments).selectinload(Shipment.items).selectinload(ShipmentItem.product),
            )
        )
        result = await session.execute(stmt)
        so = result.scalar_one_or_none()
        if not so:
            raise EntityNotFoundException("SalesOrder", so_id)
        return so


    @staticmethod
    async def list_sales_orders(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[SalesOrder], int]:
        query = select(SalesOrder)
        count_query = select(func.count(SalesOrder.id))

        if warehouse_id:
            query = query.where(SalesOrder.warehouse_id == warehouse_id)
            count_query = count_query.where(SalesOrder.warehouse_id == warehouse_id)
        if customer_id:
            query = query.where(SalesOrder.customer_id == customer_id)
            count_query = count_query.where(SalesOrder.customer_id == customer_id)
        if status:
            query = query.where(SalesOrder.status == status)
            count_query = count_query.where(SalesOrder.status == status)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(SalesOrder.id.desc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def create_sales_order(
        session: AsyncSession,
        data: SalesOrderCreate,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> SalesOrder:
        # Validate customer
        cust_res = await session.execute(select(Customer).where(Customer.id == data.customer_id))
        if not cust_res.scalar_one_or_none():
            raise EntityNotFoundException("Customer", data.customer_id)

        # Validate warehouse
        wh_res = await session.execute(select(Warehouse).where(Warehouse.id == data.warehouse_id))
        if not wh_res.scalar_one_or_none():
            raise EntityNotFoundException("Warehouse", data.warehouse_id)

        so_number = await get_next_document_number(session, "SO")

        subtotal = Decimal("0.0000")
        tax_total = Decimal("0.0000")

        so = SalesOrder(
            order_number=so_number,
            customer_id=data.customer_id,
            warehouse_id=data.warehouse_id,
            status=SalesOrderStatus.DRAFT.value,
            notes=data.notes,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(so)
        await session.flush()

        for item_in in data.items:
            prod_res = await session.execute(select(Product).where(Product.id == item_in.product_id))
            prod = prod_res.scalar_one_or_none()
            if not prod:
                raise EntityNotFoundException("Product", item_in.product_id)

            line_subtotal = item_in.unit_price * Decimal(item_in.quantity)
            line_tax = line_subtotal * (item_in.tax_rate / Decimal("100.00"))
            line_total = line_subtotal + line_tax

            subtotal += line_subtotal
            tax_total += line_tax

            so_item = SalesOrderItem(
                sales_order_id=so.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                shipped_quantity=0,
                unit_price=item_in.unit_price,
                tax_rate=item_in.tax_rate,
                line_total=line_total,
            )
            session.add(so_item)

        so.subtotal = subtotal
        so.tax_total = tax_total
        so.total_amount = subtotal + tax_total

        await session.flush()

        # Audit log
        await AuditService.record_audit(
            session=session,
            action="SALES_ORDER_CREATED",
            entity_name="SalesOrder",
            entity_id=str(so.id),
            user_id=user_id,
            user_email=user_email,
            changes={"order_number": so_number, "total_amount": str(so.total_amount)},
        )

        await session.commit()
        return await SalesService.get_by_id(session, so.id)

    @staticmethod
    async def confirm_sales_order(
        session: AsyncSession,
        so_id: int,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> SalesOrder:
        """
        Confirms order and reserves stock atomically.
        Sorts product locks to prevent deadlocks.
        Rejects operation if available stock is insufficient.
        """
        so = await SalesService.get_by_id(session, so_id)
        if so.status != SalesOrderStatus.DRAFT.value:
            raise InvalidStateTransitionException("SalesOrder", so.status, SalesOrderStatus.CONFIRMED.value)

        product_ids = [item.product_id for item in so.items]

        # Acquire row locks on stock levels strictly ordered by product_id
        stock_map = await InventoryService.get_locked_stock_levels_ordered(
            session=session,
            warehouse_id=so.warehouse_id,
            product_ids=product_ids,
        )

        # Check stock availability for all lines
        for item in so.items:
            stock = stock_map[item.product_id]
            if stock.available < item.quantity:
                raise InsufficientStockException(
                    product_id=item.product_id,
                    warehouse_id=so.warehouse_id,
                    requested=item.quantity,
                    available=stock.available,
                )

        # Apply reservations atomically
        for item in so.items:
            stock = stock_map[item.product_id]
            stock.reserved += item.quantity
            stock.version += 1

            reservation = StockReservation(
                sales_order_id=so.id,
                warehouse_id=so.warehouse_id,
                product_id=item.product_id,
                quantity=item.quantity,
                status=ReservationStatus.ACTIVE.value,
            )
            session.add(reservation)

        so.status = SalesOrderStatus.CONFIRMED.value
        so.confirmed_by = user_id
        so.confirmed_at = datetime.now(timezone.utc)
        so.updated_by = user_id

        # Audit
        await AuditService.record_audit(
            session=session,
            action="SALES_ORDER_CONFIRMED",
            entity_name="SalesOrder",
            entity_id=str(so.id),
            user_id=user_id,
            user_email=user_email,
            changes={"order_number": so.order_number, "status": so.status},
        )

        await session.commit()
        return await SalesService.get_by_id(session, so.id)


    @staticmethod
    async def ship_sales_order(
        session: AsyncSession,
        so_id: int,
        data: ShipmentCreate,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> Shipment:
        """
        Deducts stock balances (both on_hand and reserved) and records append-only ledger entries.
        Guarantees that duplicate retries cannot deduct stock twice.
        """
        so = await SalesService.get_by_id(session, so_id)
        if so.status not in (SalesOrderStatus.CONFIRMED.value, SalesOrderStatus.PARTIALLY_SHIPPED.value):
            raise InvalidStateTransitionException("SalesOrder", so.status, "SHIPPING_GOODS")

        shp_number = await get_next_document_number(session, "SHP")

        shipment = Shipment(
            shipment_number=shp_number,
            sales_order_id=so.id,
            warehouse_id=so.warehouse_id,
            tracking_number=data.tracking_number,
            carrier=data.carrier,
            shipped_by=user_id,
        )
        session.add(shipment)
        await session.flush()

        so_items_map = {item.id: item for item in so.items}
        product_ids = [so_items_map[it.sales_order_item_id].product_id for it in data.items]

        # Concurrency safety: Lock stock level rows ordered by product_id
        stock_map = await InventoryService.get_locked_stock_levels_ordered(
            session=session,
            warehouse_id=so.warehouse_id,
            product_ids=product_ids,
        )

        for ship_item_in in data.items:
            so_item = so_items_map.get(ship_item_in.sales_order_item_id)
            if not so_item:
                raise EntityNotFoundException("SalesOrderItem", ship_item_in.sales_order_item_id)

            remaining_to_ship = so_item.quantity - so_item.shipped_quantity
            if ship_item_in.quantity_shipped > remaining_to_ship:
                raise AppException(
                    f"Over-shipment rejected for product ID {so_item.product_id}. "
                    f"Ordered: {so_item.quantity}, Shipped: {so_item.shipped_quantity}, "
                    f"Attempted: {ship_item_in.quantity_shipped}."
                )

            # Update shipped quantity
            so_item.shipped_quantity += ship_item_in.quantity_shipped

            # Add shipment item
            shp_item = ShipmentItem(
                shipment_id=shipment.id,
                sales_order_item_id=so_item.id,
                product_id=so_item.product_id,
                quantity_shipped=ship_item_in.quantity_shipped,
            )
            session.add(shp_item)

            # Update stock balance: decrement on_hand AND reserved
            stock = stock_map[so_item.product_id]
            if stock.on_hand < ship_item_in.quantity_shipped or stock.reserved < ship_item_in.quantity_shipped:
                raise InsufficientStockException(
                    product_id=so_item.product_id,
                    warehouse_id=so.warehouse_id,
                    requested=ship_item_in.quantity_shipped,
                    available=stock.available,
                )

            stock.on_hand -= ship_item_in.quantity_shipped
            stock.reserved -= ship_item_in.quantity_shipped
            stock.version += 1
            await session.flush()

            # Record in append-only stock movement ledger
            await InventoryService.record_movement(
                session=session,
                warehouse_id=so.warehouse_id,
                product_id=so_item.product_id,
                quantity=ship_item_in.quantity_shipped,
                movement_type=MovementType.SALES_ISSUE,
                reference_document=shp_number,
                unit_cost=so_item.unit_price,
                actor_id=user_id,
                actor_email=user_email,
                reason=f"Shipment against {so.order_number}",
            )

        # Check if entire order is fully shipped
        is_fully_shipped = all(item.shipped_quantity >= item.quantity for item in so.items)
        so.status = (
            SalesOrderStatus.SHIPPED.value
            if is_fully_shipped
            else SalesOrderStatus.PARTIALLY_SHIPPED.value
        )
        so.updated_by = user_id

        # Audit
        await AuditService.record_audit(
            session=session,
            action="SALES_ORDER_SHIPPED",
            entity_name="Shipment",
            entity_id=str(shipment.id),
            user_id=user_id,
            user_email=user_email,
            changes={
                "shipment_number": shp_number,
                "order_number": so.order_number,
                "so_status": so.status,
            },
        )

        await session.commit()
        stmt = (
            select(Shipment)
            .where(Shipment.id == shipment.id)
            .options(
                selectinload(Shipment.items).selectinload(ShipmentItem.product)
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    @staticmethod
    async def cancel_sales_order(
        session: AsyncSession,
        so_id: int,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> SalesOrder:
        """
        Cancels sales order and safely releases reserved stock.
        """
        so = await SalesService.get_by_id(session, so_id)
        if so.status in (SalesOrderStatus.SHIPPED.value, SalesOrderStatus.PARTIALLY_SHIPPED.value, SalesOrderStatus.DELIVERED.value):
            raise InvalidStateTransitionException(
                "SalesOrder", so.status, SalesOrderStatus.CANCELLED.value
            )

        if so.status == SalesOrderStatus.CONFIRMED.value:
            # Release reservations
            res_stmt = select(StockReservation).where(
                StockReservation.sales_order_id == so.id,
                StockReservation.status == ReservationStatus.ACTIVE.value,
            )
            res_result = await session.execute(res_stmt)
            active_reservations = list(res_result.scalars().all())

            if active_reservations:
                prod_ids = [r.product_id for r in active_reservations]
                stock_map = await InventoryService.get_locked_stock_levels_ordered(
                    session=session,
                    warehouse_id=so.warehouse_id,
                    product_ids=prod_ids,
                )
                for res in active_reservations:
                    stock = stock_map[res.product_id]
                    stock.reserved = max(0, stock.reserved - res.quantity)
                    stock.version += 1
                    res.status = ReservationStatus.RELEASED.value

        so.status = SalesOrderStatus.CANCELLED.value
        so.updated_by = user_id

        await AuditService.record_audit(
            session=session,
            action="SALES_ORDER_CANCELLED",
            entity_name="SalesOrder",
            entity_id=str(so.id),
            user_id=user_id,
            user_email=user_email,
            changes={"order_number": so.order_number, "status": so.status},
        )

        await session.commit()
        return await SalesService.get_by_id(session, so.id)

