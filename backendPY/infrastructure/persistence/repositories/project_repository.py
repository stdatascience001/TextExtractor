import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import sqlalchemy as sa

from domain.repositories.project_repository import IProjectRepository
from models.models import Project, ProjectMember, ActivityEvent

class SQLAlchemyProjectRepository(IProjectRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project: Project) -> Project:
        self.session.add(project)
        return project

    async def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        stmt = select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user_id(self, user_id: uuid.UUID) -> List[Project]:
        stmt = (
            select(Project)
            .join(ProjectMember)
            .where(
                ProjectMember.user_id == user_id,
                Project.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, project: Project) -> Project:
        # Flush to check state but do not commit directly
        return project

    async def delete(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        project = (await self.session.execute(stmt)).scalar_one_or_none()
        if project:
            project.deleted_at = sa.func.now()
            # Log deletion event
            event = ActivityEvent(
                user_id=user_id,
                project_id=project_id,
                action_name="PROJECT_DELETED",
                payload={"project_name": project.name}
            )
            self.session.add(event)
