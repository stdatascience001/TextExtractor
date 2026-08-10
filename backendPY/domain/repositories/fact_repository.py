import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from models.models import Fact

class IFactRepository(ABC):
    @abstractmethod
    async def get_by_id(self, fact_id: uuid.UUID) -> Optional[Fact]:
        pass

    @abstractmethod
    async def get_active_siblings(self, project_id: uuid.UUID, subject_id: uuid.UUID, exclude_id: uuid.UUID) -> List[Fact]:
        pass

    @abstractmethod
    async def update_status(self, fact_id: uuid.UUID, status: str) -> None:
        pass
