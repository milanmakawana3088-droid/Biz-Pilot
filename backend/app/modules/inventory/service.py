from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import desc, func, select
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
from app.modules.inventory.models import (
    InventoryTransfer,
    InventoryTransferItem,
    MovementType,
    ReservationStatus,
    StockLevel,
    StockMovement,
    StockReservation,
    TransferStatus,
)
from app.modules.inventory.schemas import StockAdjustmentRequest, TransferCreateRequest
from app.modules.products.models import Product


class InventoryService:
    @staticmethod
    async def get_or_create_stock_level(
        session: AsyncSession,
        warehouse_id: int,
        product_id: int,
        for_update: bool = False,
    ) -> StockLevel:
        query = select(StockLevel).where(
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.product_id == product_id,
        )
        if for_update:
            query = query.with_for_update()

        result = await session.execute(query)
        stock = result.scalar_one_or_none()

        if not stock:
            stock = StockLevel(
                warehouse_id=warehouse_id,
                product_id=product_id,
                on_hand=0,
                reserved=0,
            )
            session.add(stock)
            await session.flush()
            if for_update:
                # Re-select for update
                query = select(StockLevel).where(StockLevel.id == stock.id).with_for_update()
                result = await session.execute(query)
                stock = result.scalar_one()

        return stock

    @staticmethod
    async def get_locked_stock_levels_ordered(
        session: AsyncSession,
        warehouse_id: int,
        product_ids: List[int],
    ) -> Dict[int, StockLevel]:
        """
        Crucial concurrency rule:
        Always acquire row locks on multiple products in strictly sorted product_id order.
        This mathematically prevents circular wait deadlocks between concurrent orders.
        """
        sorted_ids = sorted(list(set(product_ids)))
        locked_map: Dict[int, StockLevel] = {}

        for pid in sorted_ids:
            stock = await InventoryService.get_or_create_stock_level(
                session=session,
                warehouse_id=warehouse_id,
                product_id=pid,
                for_update=True,
            )
            locked_map[pid] = stock

        return locked_map

    @staticmethod
    async def record_movement(
        session: AsyncSession,
        warehouse_id: int,
        product_id: int,
        quantity: int,
        movement_type: MovementType,
        reference_document: str,
        unit_cost: Decimal = Decimal("0.0000"),
        actor_id: Optional[int] = None,
        actor_email: Optional[str] = None,
        reason: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> StockMovement:
        """
        Append-only movement ledger.
        Committed in the EXACT same database transaction as the balance change.
        """
        movement = StockMovement(
            warehouse_id=warehouse_id,
            product_id=product_id,
            quantity=quantity,
            movement_type=movement_type.value,
            reference_document=reference_document,
            unit_cost=unit_cost,
            actor_id=actor_id,
            actor_email=actor_email,
            reason=reason,
            metadata_json=metadata_json,
        )
        session.add(movement)
        await session.flush()
        return movement

    @staticmethod
    async def adjust_stock(
        session: AsyncSession,
        req: StockAdjustmentRequest,
        actor_id: Optional[int] = None,
        actor_email: Optional[str] = None,
    ) -> StockLevel:
        adj_type = req.adjustment_type.upper().strip()
        if adj_type not in (MovementType.POSITIVE_ADJUSTMENT.value, MovementType.NEGATIVE_ADJUSTMENT.value):
            raise AppException("Invalid adjustment type. Must be POSITIVE_ADJUSTMENT or NEGATIVE_ADJUSTMENT.")

        # Generate human-readable sequence number
        adj_number = await get_next_document_number(session, "ADJ")

        # Fetch product for cost valuation
        prod_stmt = select(Product).where(Product.id == req.product_id)
        prod_res = await session.execute(prod_stmt)
        product = prod_res.scalar_one_or_none()
        if not product:
            raise EntityNotFoundException("Product", req.product_id)

        # Lock stock level row FOR UPDATE
        stock = await InventoryService.get_or_create_stock_level(
            session=session,
            warehouse_id=req.warehouse_id,
            product_id=req.product_id,
            for_update=True,
        )

        if adj_type == MovementType.NEGATIVE_ADJUSTMENT.value:
            if stock.available < req.quantity:
                raise InsufficientStockException(
                    product_id=req.product_id,
                    warehouse_id=req.warehouse_id,
                    requested=req.quantity,
                    available=stock.available,
                )
            stock.on_hand -= req.quantity
            mov_type = MovementType.NEGATIVE_ADJUSTMENT
        else:
            stock.on_hand += req.quantity
            mov_type = MovementType.POSITIVE_ADJUSTMENT

        stock.version += 1
        await session.flush()

        # Record in append-only ledger
        await InventoryService.record_movement(
            session=session,
            warehouse_id=req.warehouse_id,
            product_id=req.product_id,
            quantity=req.quantity,
            movement_type=mov_type,
            reference_document=adj_number,
            unit_cost=product.cost_price,
            actor_id=actor_id,
            actor_email=actor_email,
            reason=req.reason,
        )

        # Audit log
        await AuditService.record_audit(
            session=session,
            action="STOCK_ADJUSTMENT",
            entity_name="StockLevel",
            entity_id=str(stock.id),
            user_id=actor_id,
            user_email=actor_email,
            changes={
                "warehouse_id": req.warehouse_id,
                "product_id": req.product_id,
                "type": adj_type,
                "quantity": req.quantity,
                "reason": req.reason,
                "new_on_hand": stock.on_hand,
            },
        )

        await session.commit()
        await session.refresh(stock)
        return stock

    @staticmethod
    async def create_and_execute_transfer(
        session: AsyncSession,
        req: TransferCreateRequest,
        actor_id: Optional[int] = None,
        actor_email: Optional[str] = None,
    ) -> InventoryTransfer:
        if req.source_warehouse_id == req.destination_warehouse_id:
            raise AppException("Source and destination warehouses cannot be the same.")

        transfer_number = await get_next_document_number(session, "TR")

        # Create transfer record
        transfer = InventoryTransfer(
            transfer_number=transfer_number,
            source_warehouse_id=req.source_warehouse_id,
            destination_warehouse_id=req.destination_warehouse_id,
            status=TransferStatus.COMPLETED.value,
            notes=req.notes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(transfer)
        await session.flush()

        product_ids = [it.product_id for it in req.items]

        # Lock source stock levels ordered
        source_stocks = await InventoryService.get_locked_stock_levels_ordered(
            session=session,
            warehouse_id=req.source_warehouse_id,
            product_ids=product_ids,
        )

        # Lock dest stock levels ordered
        dest_stocks = await InventoryService.get_locked_stock_levels_ordered(
            session=session,
            warehouse_id=req.destination_warehouse_id,
            product_ids=product_ids,
        )

        for item in req.items:
            # Add transfer item
            tr_item = InventoryTransferItem(
                transfer_id=transfer.id,
                product_id=item.product_id,
                quantity=item.quantity,
            )
            session.add(tr_item)

            src_stock = source_stocks[item.product_id]
            dst_stock = dest_stocks[item.product_id]

            if src_stock.available < item.quantity:
                raise InsufficientStockException(
                    product_id=item.product_id,
                    warehouse_id=req.source_warehouse_id,
                    requested=item.quantity,
                    available=src_stock.available,
                )

            # Atomic dual warehouse update
            src_stock.on_hand -= item.quantity
            src_stock.version += 1

            dst_stock.on_hand += item.quantity
            dst_stock.version += 1

            await session.flush()

            # Record TRANSFER_OUT movement for source
            await InventoryService.record_movement(
                session=session,
                warehouse_id=req.source_warehouse_id,
                product_id=item.product_id,
                quantity=item.quantity,
                movement_type=MovementType.TRANSFER_OUT,
                reference_document=transfer_number,
                actor_id=actor_id,
                actor_email=actor_email,
                reason=f"Transfer to warehouse ID {req.destination_warehouse_id}",
            )

            # Record TRANSFER_IN movement for destination
            await InventoryService.record_movement(
                session=session,
                warehouse_id=req.destination_warehouse_id,
                product_id=item.product_id,
                quantity=item.quantity,
                movement_type=MovementType.TRANSFER_IN,
                reference_document=transfer_number,
                actor_id=actor_id,
                actor_email=actor_email,
                reason=f"Transfer from warehouse ID {req.source_warehouse_id}",
            )

        # Audit
        await AuditService.record_audit(
            session=session,
            action="INVENTORY_TRANSFER",
            entity_name="InventoryTransfer",
            entity_id=str(transfer.id),
            user_id=actor_id,
            user_email=actor_email,
            changes={
                "transfer_number": transfer_number,
                "source_warehouse_id": req.source_warehouse_id,
                "destination_warehouse_id": req.destination_warehouse_id,
                "items": [{"product_id": it.product_id, "quantity": it.quantity} for it in req.items],
            },
        )

        await session.commit()
        stmt = (
            select(InventoryTransfer)
            .where(InventoryTransfer.id == transfer.id)
            .options(
                selectinload(InventoryTransfer.items).selectinload(InventoryTransferItem.product)
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one()


    @staticmethod
    async def list_stock_levels(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
        low_stock_only: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[StockLevel], int]:
        query = select(StockLevel).join(StockLevel.product)
        count_query = select(func.count(StockLevel.id)).join(StockLevel.product)

        if warehouse_id:
            query = query.where(StockLevel.warehouse_id == warehouse_id)
            count_query = count_query.where(StockLevel.warehouse_id == warehouse_id)
        if product_id:
            query = query.where(StockLevel.product_id == product_id)
            count_query = count_query.where(StockLevel.product_id == product_id)
        if low_stock_only:
            # on_hand <= reorder_level
            query = query.where(StockLevel.on_hand <= Product.reorder_level)
            count_query = count_query.where(StockLevel.on_hand <= Product.reorder_level)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Product.name.asc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def list_movements(
        session: AsyncSession,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[StockMovement], int]:
        query = select(StockMovement)
        count_query = select(func.count(StockMovement.id))

        if warehouse_id:
            query = query.where(StockMovement.warehouse_id == warehouse_id)
            count_query = count_query.where(StockMovement.warehouse_id == warehouse_id)
        if product_id:
            query = query.where(StockMovement.product_id == product_id)
            count_query = count_query.where(StockMovement.product_id == product_id)
        if movement_type:
            query = query.where(StockMovement.movement_type == movement_type)
            count_query = count_query.where(StockMovement.movement_type == movement_type)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(StockMovement.created_at)).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        return list(result.scalars().all()), total
