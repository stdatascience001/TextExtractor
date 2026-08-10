import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from domain.repositories.conflict_repository import IConflictRepository
from models.models import ConflictReport

class SQLAlchemyConflictRepository(IConflictRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, report_id: uuid.UUID) -> Optional[ConflictReport]:
        stmt = select(ConflictReport).where(ConflictReport.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_exists(self, fact_a_id: uuid.UUID, fact_b_id: uuid.UUID, conflict_type: str) -> bool:
        stmt = select(ConflictReport).where(
            and_(
                ConflictReport.conflict_type == conflict_type,
                ConflictReport.status.in_(["open", "active"]),
                or_(
                    and_(ConflictReport.first_fact_id == fact_a_id, ConflictReport.second_fact_id == fact_b_id),
                    and_(ConflictReport.first_fact_id == fact_b_id, ConflictReport.second_fact_id == fact_a_id)
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save(self, report: ConflictReport) -> None:
        self.session.add(report)
