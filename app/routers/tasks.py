from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import TaskRead, TaskUpdate
from app import crud

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskRead])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    return await crud.get_tasks(db)


@router.get("/{task_id}", response_model=TaskRead)
async def read_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int, task_in: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await crud.update_task(db, task_id, task_in)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def remove_task(task_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
