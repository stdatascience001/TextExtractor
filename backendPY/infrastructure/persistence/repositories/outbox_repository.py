import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import sqlalchemy as sa
from domain.repositories.outbox_repository import IOutboxRepository
from models.models import OutboxMessage

class SQLAlchemyOutboxRepository(IOutboxRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, message: OutboxMessage) -> None:
        self.session.add(message)

    async def get_pending(self, limit: int = 100) -> List[OutboxMessage]:
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.status == "pending")
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, message: OutboxMessage) -> None:
        # State transitions are handled on object and flushed via unit of work
        pass
