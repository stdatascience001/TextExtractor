import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from models.models import Project

class IProjectRepository(ABC):
    @abstractmethod
    async def create(self, project: Project) -> Project:
        pass

    @abstractmethod
    async def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        pass

    @abstractmethod
    async def list_by_user_id(self, user_id: uuid.UUID) -> List[Project]:
        pass

    @abstractmethod
    async def update(self, project: Project) -> Project:
        pass

    @abstractmethod
    async def delete(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        pass
