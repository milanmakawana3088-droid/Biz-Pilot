from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class DocumentSequence(Base):
    __tablename__ = "document_sequences"

    code = Column(String(50), primary_key=True)
    current_value = Column(Integer, default=0, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


async def get_next_document_number(session: AsyncSession, prefix: str) -> str:
    """
    Concurrency-safe sequence generator for business documents (PO, SO, GRN, TR, ADJ).
    Uses row-level locking (FOR UPDATE) within the active transaction to guarantee
    strictly monotonic incrementing numbers with zero collisions.
    """
    now = datetime.now(timezone.utc)
    period = now.strftime("%Y%m")
    sequence_code = f"{prefix}_{period}"

    # Lock the sequence row with FOR UPDATE
    stmt = (
        select(DocumentSequence)
        .where(DocumentSequence.code == sequence_code)
        .with_for_update()
    )
    result = await session.execute(stmt)
    seq = result.scalar_one_or_none()

    if seq is None:
        # Create sequence record initialized to 1
        seq = DocumentSequence(code=sequence_code, current_value=1)
        session.add(seq)
        await session.flush()
        next_val = 1
    else:
        seq.current_value += 1
        seq.updated_at = now
        await session.flush()
        next_val = seq.current_value

    return f"{prefix}-{period}-{next_val:04d}"
