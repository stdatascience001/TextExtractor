import uuid
import logging
from typing import List, Tuple, Optional, Any

from fastapi import HTTPException

from models.models import Project, ProjectMember, User, ActivityEvent
from domain.value_objects.project_role import ProjectRole
from application.common.unit_of_work import IUnitOfWork
from schemas.project import ProjectCreateSchema, ProjectUpdateSchema, MemberAddSchema, MemberResponseSchema

logger = logging.getLogger("project_service")

class ProjectService:
    @staticmethod
    async def create_project(
        uow: IUnitOfWork,
        creator_id: uuid.UUID,
        request: ProjectCreateSchema
    ) -> Project:
        logger.info(f"Creating project '{request.name}' for user {creator_id}")
        
        async with uow:
            project = Project(
                name=request.name,
                description=request.description
            )
            await uow.projects.create(project)
            await uow.flush() # Populate project.id

            # Register creator as owner
            member = ProjectMember(
                project_id=project.id,
                user_id=creator_id,
                role=ProjectRole.OWNER.value
            )
            await uow.members.create(member)

            # Log event
            event = ActivityEvent(
                user_id=creator_id,
                project_id=project.id,
                action_name="PROJECT_CREATED",
                payload={"project_name": project.name}
            )
            uow.add(event)
            
            await uow.commit()
            
        logger.info(f"Project {project.id} created successfully.")
        return project

    @staticmethod
    async def get_projects_for_user(
        uow: IUnitOfWork,
        user_id: uuid.UUID
    ) -> List[Project]:
        async with uow:
            return await uow.projects.list_by_user_id(user_id)

    @staticmethod
    async def get_project_details(
        uow: IUnitOfWork,
        project_id: uuid.UUID
    ) -> Tuple[Project, List[MemberResponseSchema]]:
        async with uow:
            project = await uow.projects.get_by_id(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Fetch members using repository
            members_data = await uow.members.list_members_with_users(project_id)
            
            members_list = []
            for member, user in members_data:
                members_list.append(
                    MemberResponseSchema(
                        user_id=user.id,
                        username=user.username,
                        email=user.email,
                        role=member.role,
                        created_at=member.created_at
                    )
                )
            return project, members_list

    @staticmethod
    async def update_project(
        uow: IUnitOfWork,
        project_id: uuid.UUID,
        request: ProjectUpdateSchema
    ) -> Project:
        async with uow:
            project = await uow.projects.get_by_id(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            if request.name:
                project.name = request.name
            if request.description is not None:
                project.description = request.description

            await uow.projects.update(project)
            await uow.commit()
            return project

    @staticmethod
    async def delete_project(
        uow: IUnitOfWork,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> None:
        async with uow:
            project = await uow.projects.get_by_id(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            await uow.projects.delete(project_id, user_id)
            await uow.commit()

    @staticmethod
    async def add_or_invite_member(
        uow: IUnitOfWork,
        project_id: uuid.UUID,
        request: MemberAddSchema,
        operator_id: uuid.UUID,
        db_session: Any # Keep fallback context or select directly via user utility
    ) -> dict:
        # Since User is outside Project boundary, we query user using helper select statement
        # passed via uow session helper or direct select
        from sqlalchemy import select
        stmt_user = select(User).where(User.email == request.email.lower(), User.deleted_at.is_(None))
        user = (await uow.session.execute(stmt_user)).scalar_one_or_none()

        async with uow:
            if user:
                # User exists
                existing = await uow.members.get_member(project_id, user.id)
                if existing:
                    raise HTTPException(status_code=400, detail="User is already a member of this project")

                member = ProjectMember(
                    project_id=project_id,
                    user_id=user.id,
                    role=request.role
                )
                await uow.members.create(member)

                event = ActivityEvent(
                    user_id=operator_id,
                    project_id=project_id,
                    action_name="MEMBER_ADDED",
                    payload={"added_user_id": str(user.id), "role": request.role}
                )
                uow.add(event)
                await uow.commit()
                return {"status": "added", "message": "User added to project successfully."}
            else:
                # Log pending invitation
                invitation = ActivityEvent(
                    user_id=operator_id,
                    project_id=project_id,
                    action_name="PROJECT_INVITATION",
                    payload={
                        "invitee_email": request.email.lower(),
                        "project_id": str(project_id),
                        "role": request.role,
                        "status": "pending"
                    }
                )
                uow.add(invitation)
                await uow.commit()
                return {"status": "invited", "message": "User is not registered. Pending project invitation recorded."}

    @staticmethod
    async def update_member_role(
        uow: IUnitOfWork,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: ProjectRole,
        operator_id: uuid.UUID
    ) -> None:
        async with uow:
            member = await uow.members.get_member(project_id, target_user_id)
            if not member:
                raise HTTPException(status_code=404, detail="Project member not found")

            # Block demoting the last owner
            if member.role == ProjectRole.OWNER.value and new_role != ProjectRole.OWNER:
                owners_count = await uow.members.count_owners(project_id)
                if owners_count <= 1:
                    raise HTTPException(status_code=400, detail="Cannot demote the last project owner")

            await uow.members.update_role(project_id, target_user_id, new_role)
            
            event = ActivityEvent(
                user_id=operator_id,
                project_id=project_id,
                action_name="MEMBER_ROLE_UPDATED",
                payload={"target_user_id": str(target_user_id), "new_role": new_role.value}
            )
            uow.add(event)
            await uow.commit()

    @staticmethod
    async def remove_member(
        uow: IUnitOfWork,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
        operator_id: uuid.UUID
    ) -> None:
        async with uow:
            member = await uow.members.get_member(project_id, target_user_id)
            if not member:
                raise HTTPException(status_code=404, detail="Project member not found")

            if member.role == ProjectRole.OWNER.value:
                owners_count = await uow.members.count_owners(project_id)
                if owners_count <= 1:
                    raise HTTPException(status_code=400, detail="Cannot remove the last project owner")

            await uow.members.delete(project_id, target_user_id)

            event = ActivityEvent(
                user_id=operator_id,
                project_id=project_id,
                action_name="MEMBER_REMOVED",
                payload={"removed_user_id": str(target_user_id)}
            )
            uow.add(event)
            await uow.commit()
