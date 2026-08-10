import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from domain.repositories.project_member_repository import IProjectMemberRepository
from models.models import ProjectMember, User
from domain.value_objects.project_role import ProjectRole

class SQLAlchemyProjectMemberRepository(IProjectMemberRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, member: ProjectMember) -> ProjectMember:
        self.session.add(member)
        return member

    async def get_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ProjectMember]:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_members_with_users(self, project_id: uuid.UUID) -> List[Tuple[ProjectMember, User]]:
        stmt = (
            select(ProjectMember, User)
            .join(User, ProjectMember.user_id == User.id)
            .where(ProjectMember.project_id == project_id)
        )
        res = await self.session.execute(stmt)
        # Convert all to expected Tuple type
        return [(row.ProjectMember, row.User) for row in res.all()]

    async def update_role(self, project_id: uuid.UUID, user_id: uuid.UUID, role: ProjectRole) -> None:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
        member = (await self.session.execute(stmt)).scalar_one_or_none()
        if member:
            member.role = role.value

    async def delete(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
        member = (await self.session.execute(stmt)).scalar_one_or_none()
        if member:
            await self.session.delete(member)

    async def count_owners(self, project_id: uuid.UUID) -> int:
        stmt = select(func.count(ProjectMember.id)).where(
            ProjectMember.project_id == project_id,
            ProjectMember.role == ProjectRole.OWNER.value
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0
