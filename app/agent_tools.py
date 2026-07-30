from langchain_core.tools import tool
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Task, Project


@tool
async def create_task_tool(title: str, project_id: int) -> str:
    """Create a new task with the given title under the specified project ID."""
    async with SessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if project is None:
            return f"Error: no project exists with ID {project_id}."

        task = Task(title=title, project_id=project_id)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return f"Created task {task.title} (id: {task.id}) under project {project_id}"


@tool
async def complete_task_tool(task_id: int) -> str:
    """Mark the task with the given ID as completed."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if task is None:
            return f"Error: no task exists with ID {task_id}."

        task.completed = True
        await db.commit()
        return f"Marked task {task.title} (id: {task.id}) as completed."


@tool
async def list_projects_tool() -> str:
    """List all existing projects with their IDs, so the user can reference them by name."""
    async with SessionLocal() as db:
        result = await db.execute(select(Project))
        projects = result.scalars().all()

        if not projects:
            return "No projects found."

        return "\n".join(f"- id={p.id}: {p.name}" for p in projects)


@tool
async def list_tasks_tool(project_id: int) -> str:
    """List all tasks under the specified project ID."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.project_id == project_id))
        tasks = result.scalars().all()

        if not tasks:
            return "No tasks found."

        return "\n".join(f"- {t.title}" for t in tasks)


@tool
async def list_completed_tasks_tool(project_id: int) -> str:
    """List all completed tasks under the specified project ID."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .where(Task.completed == True)
        )
        tasks = result.scalars().all()

        if not tasks:
            return "No completed tasks found."

        return "\n".join(f"- {t.title}" for t in tasks)


@tool
async def list_uncompleted_tasks_tool(project_id: int) -> str:
    """List all uncompleted tasks under the specified project ID."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .where(Task.completed == False)
        )
        tasks = result.scalars().all()

        if not tasks:
            return "No uncompleted tasks found."

        return "\n".join(f"- {t.title}" for t in tasks)


tools = [
    create_task_tool,
    complete_task_tool,
    list_projects_tool,
    list_tasks_tool,
    list_completed_tasks_tool,
    list_uncompleted_tasks_tool,
]
