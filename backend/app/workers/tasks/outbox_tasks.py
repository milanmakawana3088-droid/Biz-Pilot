import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.logging import logger
from app.db.session import async_session_factory
from app.modules.audit.models import OutboxEvent
from app.workers.celery_app import celery_app


async def _publish_pending_outbox_events_async():
    async with async_session_factory() as session:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.created_at.asc())
            .limit(100)
        )
        result = await session.execute(stmt)
        events = list(result.scalars().all())

        for ev in events:
            try:
                # Dispatch to external consumers or message bus
                logger.info(
                    f"Publishing outbox event #{ev.id}: {ev.event_type} for aggregate {ev.aggregate_type} ({ev.aggregate_id})",
                    extra={"event_id": ev.id, "event_type": ev.event_type},
                )
                ev.status = "PUBLISHED"
                ev.processed_at = datetime.now(timezone.utc)
            except Exception as ex:
                logger.error(f"Failed to publish outbox event #{ev.id}: {str(ex)}")
                ev.retry_count += 1
                if ev.retry_count > 5:
                    ev.status = "FAILED"

        await session.commit()
        return len(events)


@celery_app.task(name="app.workers.tasks.outbox_tasks.publish_pending_outbox_events")
def publish_pending_outbox_events():
    """Celery task running on schedule to poll and dispatch pending transactional outbox events."""
    return asyncio.run(_publish_pending_outbox_events_async())
