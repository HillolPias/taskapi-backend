from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Task, Project
from app.schemas import TaskUpdate, ProjectCreate, TaskCreateNested


async def create_project(db: AsyncSession, project_in: ProjectCreate) -> Project:
    project = Project(name=project_in.name)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project))
    return list(result.scalars().all())


async def get_project_with_tasks(db: AsyncSession, project_id: int) -> Project | None:
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks))
        .where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def create_task_for_project(
    db: AsyncSession, project_id: int, task_in: TaskCreateNested
) -> Task | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        return None

    task = Task(title=task_in.title, project_id=project_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_project(db: AsyncSession, project_id: int) -> bool:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        return False
    await db.delete(project)
    await db.commit()
    return True


async def get_tasks(db: AsyncSession) -> list[Task]:
    result = await db.execute(select(Task))
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    task = await get_task(db, task_id)
    if task is None:
        return False
    await db.delete(task)
    await db.commit()
    return True


async def update_task(
    db: AsyncSession, task_id: int, task_in: TaskUpdate
) -> Task | None:
    task = await get_task(db, task_id)
    if task is None:
        return None
    update_data = task_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task
