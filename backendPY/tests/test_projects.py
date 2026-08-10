import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from domain.value_objects.project_role import ProjectRole
from models.models import Project, ProjectMember, User, ActivityEvent
from services.project_service import ProjectService
from schemas.project import ProjectCreateSchema, ProjectUpdateSchema, MemberAddSchema

@pytest.mark.asyncio
async def test_create_project():
    # Arrange
    mock_uow = MagicMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.projects = MagicMock()
    mock_uow.members = MagicMock()
    
    mock_uow.projects.create = AsyncMock(return_value=None)
    mock_uow.flush = AsyncMock()
    mock_uow.members.create = AsyncMock()
    mock_uow.add = MagicMock()
    mock_uow.commit = AsyncMock()

    creator_id = uuid.uuid4()
    request = ProjectCreateSchema(name="Test Project", description="Testing clean architecture")

    # Act
    project = await ProjectService.create_project(mock_uow, creator_id, request)

    # Assert
    assert project.name == "Test Project"
    assert project.description == "Testing clean architecture"
    mock_uow.projects.create.assert_called_once()
    mock_uow.members.create.assert_called_once()
    mock_uow.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_project_details_success():
    # Arrange
    mock_uow = MagicMock()
    mock_uow.__aenter__.return_value = mock_uow
    
    project_id = uuid.uuid4()
    mock_project = Project(id=project_id, name="Sandbox", description="Mocked")
    mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

    mock_member = ProjectMember(user_id=uuid.uuid4(), role=ProjectRole.OWNER.value)
    mock_user = User(id=mock_member.user_id, username="testuser", email="test@example.com")
    
    mock_uow.members.list_members_with_users = AsyncMock(return_value=[(mock_member, mock_user)])

    # Act
    project, members = await ProjectService.get_project_details(mock_uow, project_id)

    # Assert
    assert project.id == project_id
    assert len(members) == 1
    assert members[0].username == "testuser"
    assert members[0].role == ProjectRole.OWNER.value

@pytest.mark.asyncio
async def test_update_project():
    # Arrange
    mock_uow = MagicMock()
    mock_uow.__aenter__.return_value = mock_uow
    
    project_id = uuid.uuid4()
    mock_project = Project(id=project_id, name="Old Name", description="Old Desc")
    mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
    mock_uow.projects.update = AsyncMock()
    mock_uow.commit = AsyncMock()

    request = ProjectUpdateSchema(name="New Name", description="New Desc")

    # Act
    project = await ProjectService.update_project(mock_uow, project_id, request)

    # Assert
    assert project.name == "New Name"
    assert project.description == "New Desc"
    mock_uow.projects.update.assert_called_once()
    mock_uow.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_project():
    # Arrange
    mock_uow = MagicMock()
    mock_uow.__aenter__.return_value = mock_uow
    
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_project = Project(id=project_id, name="To Delete")
    mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
    mock_uow.projects.delete = AsyncMock()
    mock_uow.commit = AsyncMock()

    # Act
    await ProjectService.delete_project(mock_uow, project_id, user_id)

    # Assert
    mock_uow.projects.delete.assert_called_once_with(project_id, user_id)
    mock_uow.commit.assert_called_once()

@pytest.mark.asyncio
async def test_demote_last_owner_protection():
    # Arrange
    mock_uow = MagicMock()
    mock_uow.__aenter__.return_value = mock_uow
    
    project_id = uuid.uuid4()
    target_user_id = uuid.uuid4()
    
    mock_member = ProjectMember(user_id=target_user_id, role=ProjectRole.OWNER.value)
    mock_uow.members.get_member = AsyncMock(return_value=mock_member)
    mock_uow.members.count_owners = AsyncMock(return_value=1) # Only 1 owner exists

    from fastapi import HTTPException
    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        await ProjectService.update_member_role(
            mock_uow,
            project_id,
            target_user_id,
            ProjectRole.ADMIN,
            uuid.uuid4()
        )
    assert exc.value.status_code == 400
    assert "Cannot demote the last project owner" in exc.value.detail

@pytest.mark.asyncio
async def test_remove_last_owner_protection():
    # Arrange
    mock_uow = MagicMock()
    mock_uow.__aenter__.return_value = mock_uow
    
    project_id = uuid.uuid4()
    target_user_id = uuid.uuid4()
    
    mock_member = ProjectMember(user_id=target_user_id, role=ProjectRole.OWNER.value)
    mock_uow.members.get_member = AsyncMock(return_value=mock_member)
    mock_uow.members.count_owners = AsyncMock(return_value=1) # Only 1 owner exists

    from fastapi import HTTPException
    # Act & Assert
    with pytest.raises(HTTPException) as exc:
        await ProjectService.remove_member(
            mock_uow,
            project_id,
            target_user_id,
            uuid.uuid4()
        )
    assert exc.value.status_code == 400
    assert "Cannot remove the last project owner" in exc.value.detail
