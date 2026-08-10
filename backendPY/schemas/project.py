import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ProjectCreateSchema(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)

class ProjectUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)

class ProjectResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MemberAddSchema(BaseModel):
    email: str = Field(description="Email of the user to add or invite")
    role: str = Field(default="viewer", description="Viewer, reviewer, admin, or owner")

class MemberUpdateSchema(BaseModel):
    role: str = Field(description="New role to assign: viewer, reviewer, admin, owner")

class MemberResponseSchema(BaseModel):
    user_id: uuid.UUID
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectDetailResponseSchema(ProjectResponseSchema):
    members: List[MemberResponseSchema] = []
