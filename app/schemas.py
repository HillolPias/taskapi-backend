from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class TaskUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    completed: bool
    created_at: datetime
    project_id: int


class ProjectReadWithTasks(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    tasks: list[TaskRead]


class TaskCreateNested(BaseModel):
    title: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
