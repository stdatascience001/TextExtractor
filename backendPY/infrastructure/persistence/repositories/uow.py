from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from application.common.unit_of_work import IUnitOfWork
from infrastructure.persistence.repositories.project_repository import SQLAlchemyProjectRepository
from infrastructure.persistence.repositories.project_member_repository import SQLAlchemyProjectMemberRepository
from infrastructure.persistence.repositories.fact_repository import SQLAlchemyFactRepository
from infrastructure.persistence.repositories.conflict_repository import SQLAlchemyConflictRepository
from infrastructure.persistence.repositories.outbox_repository import SQLAlchemyOutboxRepository

class SQLAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.projects = SQLAlchemyProjectRepository(session)
        self.members = SQLAlchemyProjectMemberRepository(session)
        self.facts = SQLAlchemyFactRepository(session)
        self.conflicts = SQLAlchemyConflictRepository(session)
        self.outbox = SQLAlchemyOutboxRepository(session)

    def add(self, entity: Any) -> None:
        self.session.add(entity)

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def flush(self):
        await self.session.flush()
