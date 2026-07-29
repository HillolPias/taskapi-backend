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


tools = [create_task_tool, complete_task_tool, list_projects_tool]
