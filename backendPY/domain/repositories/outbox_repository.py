import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from models.models import OutboxMessage

class IOutboxRepository(ABC):
    @abstractmethod
    async def save(self, message: OutboxMessage) -> None:
        pass

    @abstractmethod
    async def get_pending(self, limit: int = 100) -> List[OutboxMessage]:
        pass

    @abstractmethod
    async def update(self, message: OutboxMessage) -> None:
        pass
