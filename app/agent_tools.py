from langchain_core.tools import tool
from sqlalchemy import select, func

from app.database import SessionLocal
from app.models import Task, Project
from app.rag import retrieve_relevant_context
from typing import Literal


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
async def get_project_by_name_tool(name: str) -> str:
    """Find a project by (partial, case-insensitive) name match."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(Project).where(Project.name.ilike(f"%{name}%"))
        )
        projects = result.scalars().all()

        if not projects:
            return f"No project found with name '{name}'."
        if len(projects) > 1:
            listing = ", ".join(f"'{p.name}' (id={p.id})" for p in projects)
            return f"Multiple projects match '{name}': {listing}. Please ask which one they mean."
        p = projects[0]
        return f"Project '{p.name}' has ID {p.id}"


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
async def list_tasks_tool(
    project_id: int | None = None,
    status: Literal["all", "completed", "pending"] = "all",
) -> str:
    """List tasks, always including their IDs so they can be referenced in
    follow-up actions. Filter by project_id (omit to search across all projects)
    and/or status ('completed', 'pending', or 'all')."""
    async with SessionLocal() as db:
        query = select(Task)
        if project_id is not None:
            query = query.where((Task.project_id == project_id))
        if status == "completed":
            query = query.where(Task.completed == True)
        elif status == "pending":
            query = query.where(Task.completed == False)
        result = await db.execute(query)
        tasks = result.scalars().all()
        if not tasks:
            return "No matching tasks found."
        return "\n".join(
            f"{t.id}. {t.title} ({'✓' if t.completed else '✗'})" for t in tasks
        )


@tool
async def create_project_tool(name: str) -> str:
    """Create a new project."""
    async with SessionLocal() as db:
        project = Project(name=name)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return f"Created project '{project.name}' (id: {project.id})."


@tool
async def delete_task_tool(task_id: int) -> str:
    """Delete a task by ID."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return f"No task found with ID {task_id}."
        await db.delete(task)
        await db.commit()
        return f"Deleted task '{task.title}'."


@tool
async def rename_task_tool(task_id: int, new_title: str) -> str:
    """Rename a task by ID."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return f"No task found with ID {task_id}."
        old = task.title
        task.title = new_title
        await db.commit()
        return f"Renamed '{old}' to '{new_title}'."


@tool
async def uncomplete_task_tool(task_id: int) -> str:
    """Mark a completed task as incomplete."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return f"No task found with ID {task_id}."
        task.completed = False
        await db.commit()
        return f"Marked '{task.title}' as incomplete."


@tool
async def search_tasks_tool(keyword: str) -> str:
    """Exact/partial keyword search over task titles only (case-insensitive
    substring match). Use this when the user gives a specific word they expect
    literally in a task title. For broader natural-language questions about
    status, meaning, or themes, use search_tasks_and_projects_tool instead."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.title.ilike(f"%{keyword}%")))
        tasks = result.scalars().all()
        if not tasks:
            return "No matching tasks found."
        return "\n".join(f"{t.id}. {t.title}" for t in tasks)


@tool
async def search_tasks_and_projects_tool(query: str) -> str:
    """Semantic search across tasks and projects for natural-language questions
    (e.g. 'what's still pending', 'what projects do I have', 'anything backend-related').
    Prefer this over search_tasks_tool unless the user gives an exact keyword or phrase.
    """
    chunks = retrieve_relevant_context(query, k=5)
    if not chunks:
        return "No relevant tasks or projects found for this query."
    return "\n".join(chunks)


@tool
async def move_task_tool(task_id: int, project_id: int) -> str:
    """Move a task to another project."""
    async with SessionLocal() as db:
        task_result = await db.execute(select(Task).where(Task.id == task_id))
        task = task_result.scalar_one_or_none()
        if task is None:
            return "Task not found."
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if project is None:
            return "Destination project not found."
        task.project_id = project_id
        await db.commit()
        return f"Moved '{task.title}' to project '{project.name}'."


@tool
async def count_tasks_tool(project_id: int) -> str:
    """Count the number of tasks in a project."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        count = result.scalar()
        return f"Project has {count} task(s)."


@tool
async def project_progress_tool(project_id: int) -> str:
    """Show project completion progress."""
    async with SessionLocal() as db:
        total_result = await db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        total = total_result.scalar()
        completed_result = await db.execute(
            select(func.count(Task.id))
            .where(Task.project_id == project_id)
            .where(Task.completed == True)
        )
        completed = completed_result.scalar()
        if total == 0:
            return "Project has no tasks."
        percentage = completed * 100 / total
        return f"{completed}/{total} tasks completed " f"({percentage:.1f}%)."


@tool
async def delete_project_tool(project_id: int) -> str:
    """Delete a project."""
    async with SessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            return "Project not found."
        await db.delete(project)
        await db.commit()
        return f"Deleted project '{project.name}'."


@tool
async def get_task_tool(task_id: int) -> str:
    """Get detailed information about a task."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return "Task not found."
        return (
            f"ID: {task.id}\n"
            f"Title: {task.title}\n"
            f"Project ID: {task.project_id}\n"
            f"Completed: {task.completed}"
        )


@tool
async def complete_all_tasks_tool(project_id: int) -> str:
    """Mark every task in a project as completed."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.project_id == project_id))
        tasks = result.scalars().all()
        if not tasks:
            return "No tasks found."
        for task in tasks:
            task.completed = True
        await db.commit()
        return f"Completed {len(tasks)} task(s)."


tools = [
    create_task_tool,
    get_project_by_name_tool,
    complete_task_tool,
    list_projects_tool,
    list_tasks_tool,
    create_project_tool,
    delete_task_tool,
    rename_task_tool,
    uncomplete_task_tool,
    search_tasks_tool,
    search_tasks_and_projects_tool,
    move_task_tool,
    count_tasks_tool,
    project_progress_tool,
    delete_project_tool,
    get_task_tool,
    complete_all_tasks_tool,
]
