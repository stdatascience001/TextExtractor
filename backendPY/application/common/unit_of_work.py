from abc import ABC, abstractmethod
from typing import Any
from domain.repositories.project_repository import IProjectRepository
from domain.repositories.project_member_repository import IProjectMemberRepository
from domain.repositories.fact_repository import IFactRepository
from domain.repositories.conflict_repository import IConflictRepository
from domain.repositories.outbox_repository import IOutboxRepository

class IUnitOfWork(ABC):
    projects: IProjectRepository
    members: IProjectMemberRepository
    facts: IFactRepository
    conflicts: IConflictRepository
    outbox: IOutboxRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    def add(self, entity: Any) -> None:
        pass

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass

    @abstractmethod
    async def flush(self):
        pass

