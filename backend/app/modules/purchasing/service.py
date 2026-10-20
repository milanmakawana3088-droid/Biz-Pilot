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
    InvalidStateTransitionException,
)
from app.modules.audit.service import AuditService
from app.modules.inventory.models import MovementType
from app.modules.inventory.service import InventoryService
from app.modules.locations.models import Warehouse
from app.modules.products.models import Product
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.modules.purchasing.schemas import (
    GoodsReceiptCreate,
    PurchaseOrderCreate,
)
from app.modules.suppliers.models import Supplier


class PurchasingService:
    @staticmethod
    async def get_by_id(session: AsyncSession, po_id: int) -> PurchaseOrder:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.warehouse),
                selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product),
                selectinload(PurchaseOrder.receipts).selectinload(GoodsReceipt.items).selectinload(GoodsReceiptItem.product),
            )
        )
        result = await session.execute(stmt)
        po = result.scalar_one_or_none()
        if not po:
            raise EntityNotFoundException("PurchaseOrder", po_id)
        return po


    @staticmethod
    async def list_purchase_orders(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[PurchaseOrder], int]:
        query = select(PurchaseOrder)
        count_query = select(func.count(PurchaseOrder.id))

        if warehouse_id:
            query = query.where(PurchaseOrder.warehouse_id == warehouse_id)
            count_query = count_query.where(PurchaseOrder.warehouse_id == warehouse_id)
        if supplier_id:
            query = query.where(PurchaseOrder.supplier_id == supplier_id)
            count_query = count_query.where(PurchaseOrder.supplier_id == supplier_id)
        if status:
            query = query.where(PurchaseOrder.status == status)
            count_query = count_query.where(PurchaseOrder.status == status)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(PurchaseOrder.id.desc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def create_purchase_order(
        session: AsyncSession,
        data: PurchaseOrderCreate,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> PurchaseOrder:
        # Validate supplier
        supp_res = await session.execute(select(Supplier).where(Supplier.id == data.supplier_id))
        if not supp_res.scalar_one_or_none():
            raise EntityNotFoundException("Supplier", data.supplier_id)

        # Validate warehouse
        wh_res = await session.execute(select(Warehouse).where(Warehouse.id == data.warehouse_id))
        if not wh_res.scalar_one_or_none():
            raise EntityNotFoundException("Warehouse", data.warehouse_id)

        po_number = await get_next_document_number(session, "PO")

        subtotal = Decimal("0.0000")
        tax_total = Decimal("0.0000")

        po = PurchaseOrder(
            order_number=po_number,
            supplier_id=data.supplier_id,
            warehouse_id=data.warehouse_id,
            status=PurchaseOrderStatus.DRAFT.value,
            notes=data.notes,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(po)
        await session.flush()

        for item_in in data.items:
            # Check product
            prod_res = await session.execute(select(Product).where(Product.id == item_in.product_id))
            prod = prod_res.scalar_one_or_none()
            if not prod:
                raise EntityNotFoundException("Product", item_in.product_id)

            line_subtotal = item_in.unit_cost * Decimal(item_in.quantity)
            line_tax = line_subtotal * (item_in.tax_rate / Decimal("100.00"))
            line_total = line_subtotal + line_tax

            subtotal += line_subtotal
            tax_total += line_tax

            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                received_quantity=0,
                unit_cost=item_in.unit_cost,
                tax_rate=item_in.tax_rate,
                line_total=line_total,
            )
            session.add(po_item)

        po.subtotal = subtotal
        po.tax_total = tax_total
        po.total_amount = subtotal + tax_total

        await session.flush()

        # Audit log
        await AuditService.record_audit(
            session=session,
            action="PURCHASE_ORDER_CREATED",
            entity_name="PurchaseOrder",
            entity_id=str(po.id),
            user_id=user_id,
            user_email=user_email,
            changes={"order_number": po_number, "total_amount": str(po.total_amount)},
        )

        await session.commit()
        return await PurchasingService.get_by_id(session, po.id)

    @staticmethod
    async def approve_purchase_order(
        session: AsyncSession,
        po_id: int,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> PurchaseOrder:
        po = await PurchasingService.get_by_id(session, po_id)
        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise InvalidStateTransitionException("PurchaseOrder", po.status, PurchaseOrderStatus.APPROVED.value)

        po.status = PurchaseOrderStatus.APPROVED.value
        po.approved_by = user_id
        po.approved_at = datetime.now(timezone.utc)
        po.updated_by = user_id

        await AuditService.record_audit(
            session=session,
            action="PURCHASE_ORDER_APPROVED",
            entity_name="PurchaseOrder",
            entity_id=str(po.id),
            user_id=user_id,
            user_email=user_email,
            changes={"order_number": po.order_number, "status": po.status},
        )

        await session.commit()
        return await PurchasingService.get_by_id(session, po.id)


    @staticmethod
    async def receive_goods(
        session: AsyncSession,
        po_id: int,
        data: GoodsReceiptCreate,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> GoodsReceipt:
        po = await PurchasingService.get_by_id(session, po_id)
        if po.status not in (PurchaseOrderStatus.APPROVED.value, PurchaseOrderStatus.PARTIALLY_RECEIVED.value):
            raise InvalidStateTransitionException(
                "PurchaseOrder", po.status, "RECEIVING_GOODS"
            )

        grn_number = await get_next_document_number(session, "GRN")

        receipt = GoodsReceipt(
            receipt_number=grn_number,
            purchase_order_id=po.id,
            warehouse_id=po.warehouse_id,
            notes=data.notes,
            received_by=user_id,
        )
        session.add(receipt)
        await session.flush()

        po_items_map = {item.id: item for item in po.items}
        product_ids = [po_items_map[it.purchase_order_item_id].product_id for it in data.items]

        # Concurrency safety: Lock stock level rows ordered by product_id
        stock_map = await InventoryService.get_locked_stock_levels_ordered(
            session=session,
            warehouse_id=po.warehouse_id,
            product_ids=product_ids,
        )

        for rec_item in data.items:
            po_item = po_items_map.get(rec_item.purchase_order_item_id)
            if not po_item:
                raise EntityNotFoundException("PurchaseOrderItem", rec_item.purchase_order_item_id)

            remaining_to_receive = po_item.quantity - po_item.received_quantity
            if rec_item.quantity_received > remaining_to_receive:
                raise AppException(
                    f"Over-receipt rejected for product ID {po_item.product_id}. "
                    f"Ordered: {po_item.quantity}, Already received: {po_item.received_quantity}, "
                    f"Attempted: {rec_item.quantity_received}."
                )

            # Update PO item received quantity
            po_item.received_quantity += rec_item.quantity_received

            # Add goods receipt item
            gr_item = GoodsReceiptItem(
                goods_receipt_id=receipt.id,
                purchase_order_item_id=po_item.id,
                product_id=po_item.product_id,
                quantity_received=rec_item.quantity_received,
                unit_cost=po_item.unit_cost,
            )
            session.add(gr_item)

            # Update stock balance atomically
            stock = stock_map[po_item.product_id]
            stock.on_hand += rec_item.quantity_received
            stock.version += 1
            await session.flush()

            # Record in append-only stock movement ledger
            await InventoryService.record_movement(
                session=session,
                warehouse_id=po.warehouse_id,
                product_id=po_item.product_id,
                quantity=rec_item.quantity_received,
                movement_type=MovementType.PURCHASE_RECEIPT,
                reference_document=grn_number,
                unit_cost=po_item.unit_cost,
                actor_id=user_id,
                actor_email=user_email,
                reason=f"Receipt against {po.order_number}",
            )

        # Check if entire PO is fully received
        is_fully_received = all(item.received_quantity >= item.quantity for item in po.items)
        po.status = (
            PurchaseOrderStatus.RECEIVED.value
            if is_fully_received
            else PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        )
        po.updated_by = user_id

        # Audit
        await AuditService.record_audit(
            session=session,
            action="GOODS_RECEIVED",
            entity_name="GoodsReceipt",
            entity_id=str(receipt.id),
            user_id=user_id,
            user_email=user_email,
            changes={
                "receipt_number": grn_number,
                "order_number": po.order_number,
                "po_status": po.status,
            },
        )

        await session.commit()
        stmt = (
            select(GoodsReceipt)
            .where(GoodsReceipt.id == receipt.id)
            .options(
                selectinload(GoodsReceipt.items).selectinload(GoodsReceiptItem.product)
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    @staticmethod
    async def cancel_purchase_order(
        session: AsyncSession,
        po_id: int,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> PurchaseOrder:
        po = await PurchasingService.get_by_id(session, po_id)
        if po.status in (PurchaseOrderStatus.RECEIVED.value, PurchaseOrderStatus.PARTIALLY_RECEIVED.value):
            raise InvalidStateTransitionException(
                "PurchaseOrder", po.status, PurchaseOrderStatus.CANCELLED.value
            )

        po.status = PurchaseOrderStatus.CANCELLED.value
        po.updated_by = user_id

        await AuditService.record_audit(
            session=session,
            action="PURCHASE_ORDER_CANCELLED",
            entity_name="PurchaseOrder",
            entity_id=str(po.id),
            user_id=user_id,
            user_email=user_email,
            changes={"order_number": po.order_number, "status": po.status},
        )

        await session.commit()
        return await PurchasingService.get_by_id(session, po.id)

