import json
from typing import Any, Dict, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog, IdempotencyRecord, OutboxEvent


class AuditService:
    @staticmethod
    async def record_audit(
        session: AsyncSession,
        action: str,
        entity_name: str,
        entity_id: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        changes_json = json.dumps(changes) if changes is not None else None
        log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_name=entity_name,
            entity_id=str(entity_id),
            changes=changes_json,
            ip_address=ip_address,
        )
        session.add(log)
        await session.flush()
        return log

    @staticmethod
    async def record_outbox(
        session: AsyncSession,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=json.dumps(payload),
        )
        session.add(event)
        await session.flush()
        return event

    @staticmethod
    async def get_idempotency_record(
        session: AsyncSession,
        key: str,
    ) -> Optional[IdempotencyRecord]:
        stmt = select(IdempotencyRecord).where(IdempotencyRecord.key == key)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def save_idempotency_record(
        session: AsyncSession,
        key: str,
        endpoint: str,
        request_hash: str,
        status_code: int,
        response_body: str,
    ) -> IdempotencyRecord:
        record = IdempotencyRecord(
            key=key,
            endpoint=endpoint,
            request_hash=request_hash,
            status_code=status_code,
            response_body=response_body,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def list_audit_logs(
        session: AsyncSession,
        page: int = 1,
        size: int = 50,
        entity_name: Optional[str] = None,
        action: Optional[str] = None,
    ):
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if entity_name:
            query = query.where(AuditLog.entity_name == entity_name)
            count_query = count_query.where(AuditLog.entity_name == entity_name)
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)

        total_res = await session.execute(count_query)
        total = total_res.scalar() or 0

        query = (
            query.order_by(desc(AuditLog.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await session.execute(query)
        items = result.scalars().all()
        return items, total
