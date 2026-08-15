from datetime import date, timedelta
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
    due_within_days: int | None = None,
) -> str:
    """List tasks with exact, structured data (IDs, completion status, due dates)
    from the database. ALWAYS use this tool — not search_tasks_and_projects_tool —
    for any question involving due dates, deadlines, or date ranges (e.g. 'what's
    due this week', 'what's due in 3 days', 'show overdue tasks'), since only this
    tool has access to due date data.

    Filter by project_id (omit to search across all projects), status ('completed',
    'pending', or 'all'), and optionally due_within_days (e.g. 7 for 'due this week').

    IMPORTANT: due_within_days only returns tasks that HAVE a due date set and
    fall within that range (including already-overdue tasks). Tasks with no due
    date are never included in a due_within_days-filtered result — they are not
    counted as "not due," they simply have no date recorded. The result always
    reports how many undated tasks exist separately, so you have that context
    when answering the user."""
    async with SessionLocal() as db:
        query = select(Task)
        if project_id is not None:
            query = query.where((Task.project_id == project_id))
        if status == "completed":
            query = query.where(Task.completed == True)
        elif status == "pending":
            query = query.where(Task.completed == False)

        if due_within_days is not None:
            cutoff = date.today() + timedelta(days=due_within_days)
            query = query.where(Task.due_date.isnot(None)).where(
                Task.due_date <= cutoff
            )

        result = await db.execute(query)
        tasks = result.scalars().all()

        lines = []
        if not tasks:
            return "No matching tasks found."
        else:
            for t in tasks:
                due_str = f", due {t.due_date}" if t.due_date else ""
                lines.append(
                    f"{t.id}. {t.title} ({'✓' if t.completed else '✗'}{due_str})"
                )

        if due_within_days is not None:
            undated_query = (
                select(func.count(Task.id))
                .where(Task.due_date.is_(None))
                .where(Task.completed == False)
            )
            if project_id is not None:
                undated_query = undated_query.where(Task.project_id == project_id)
            undated_count = (await db.execute(undated_query)).scalar()
            if undated_count:
                lines.append(
                    f"\n(Note: {undated_count} other incomplete task(s) have no due date set - not included above.)"
                )

        return "\n".join(lines)


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
    """Semantic/fuzzy search across tasks and projects by MEANING or THEME ONLY
    (e.g. 'anything backend-related', 'what projects do I have', 'tasks about design').

    DO NOT use this tool for ANY question mentioning: due dates, deadlines, "due
    this week", "due in X days", "overdue", or any date/time range. This tool has
    NO due date information whatsoever — it will return incomplete or misleading
    results for date-based questions. Use list_tasks_tool for ALL date-related
    queries instead, even if the phrasing sounds like a general search."""
    async with SessionLocal() as db:
        result = await db.execute(select(Task).where(Task.title.ilike(f"%{keyword}%")))
        tasks = result.scalars().all()
        if not tasks:
            return "No matching tasks found."
        return "\n".join(f"{t.id}. {t.title}" for t in tasks)


@tool
async def search_tasks_and_projects_tool(query: str) -> str:
    """Semantic/fuzzy search across tasks and projects by MEANING or THEME
    (e.g. 'anything backend-related', 'what projects do I have'). Does NOT
    include due date information — never use this for date/deadline-related
    questions; use list_tasks_tool instead for those.
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
