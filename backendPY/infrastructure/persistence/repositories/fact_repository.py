import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from domain.repositories.fact_repository import IFactRepository
from models.models import Fact

class SQLAlchemyFactRepository(IFactRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, fact_id: uuid.UUID) -> Optional[Fact]:
        stmt = select(Fact).where(Fact.id == fact_id, Fact.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_siblings(self, project_id: uuid.UUID, subject_id: uuid.UUID, exclude_id: uuid.UUID) -> List[Fact]:
        stmt = select(Fact).where(
            and_(
                Fact.project_id == project_id,
                Fact.subject_id == subject_id,
                Fact.id != exclude_id,
                Fact.deleted_at.is_(None),
                Fact.status.in_(["pending", "verified", "unverified", "conflicted"])
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, fact_id: uuid.UUID, status: str) -> None:
        fact = await self.get_by_id(fact_id)
        if fact:
            fact.status = status
