import uuid
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from models.models import ProjectMember, User
from domain.value_objects.project_role import ProjectRole

class IProjectMemberRepository(ABC):
    @abstractmethod
    async def create(self, member: ProjectMember) -> ProjectMember:
        pass

    @abstractmethod
    async def get_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ProjectMember]:
        pass

    @abstractmethod
    async def list_members_with_users(self, project_id: uuid.UUID) -> List[Tuple[ProjectMember, User]]:
        pass

    @abstractmethod
    async def update_role(self, project_id: uuid.UUID, user_id: uuid.UUID, role: ProjectRole) -> None:
        pass

    @abstractmethod
    async def delete(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    async def count_owners(self, project_id: uuid.UUID) -> int:
        pass
