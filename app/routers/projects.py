from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectReadWithTasks,
    TaskRead,
    TaskCreateNested,
)
from app import crud

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectRead, status_code=201)
async def create_project(project_in: ProjectCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_project(db, project_in)


@router.get("/", response_model=list[ProjectRead])
async def list_projects(db: AsyncSession = Depends(get_db)):
    return await crud.get_projects(db)


@router.get("/{project_id}", response_model=ProjectReadWithTasks)
async def read_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await crud.get_project_with_tasks(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task_for_project(
    project_id: int, task_in: TaskCreateNested, db: AsyncSession = Depends(get_db)
):
    task = await crud.create_task_for_project(db, project_id, task_in)
    if task is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return task


@router.delete("/{project_id}", status_code=204)
async def remove_project(project_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
