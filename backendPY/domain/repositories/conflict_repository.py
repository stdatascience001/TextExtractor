import uuid
from abc import ABC, abstractmethod
from typing import Optional, List
from models.models import ConflictReport

class IConflictRepository(ABC):
    @abstractmethod
    async def get_by_id(self, report_id: uuid.UUID) -> Optional[ConflictReport]:
        pass

    @abstractmethod
    async def check_exists(self, fact_a_id: uuid.UUID, fact_b_id: uuid.UUID, conflict_type: str) -> bool:
        pass

    @abstractmethod
    async def save(self, report: ConflictReport) -> None:
        pass
