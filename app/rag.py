from langchain_chroma import Chroma
from langchain_core.documents import Document

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Project
from app.llm import embeddings

vector_store = Chroma(
    collection_name="tasks_projects",
    embedding_function=embeddings,
    persist_directory="./chroma_data",
)


async def build_index(db: AsyncSession) -> int:
    """Rebuild the vector index from current Postgres data."""
    result = await db.execute(select(Project).options(selectinload(Project.tasks)))
    projects = result.scalars().all()
    documents = []
    for project in projects:
        for task in project.tasks:
            status = "completed" if task.completed else "not completed"
            text = f"Task {task.title} in project {project.name} is {status}."
            documents.append(
                Document(
                    page_content=text,
                    metadata={"task_id": task.id, "project_id": project.id},
                )
            )

    # Clear existing index, then add the fresh set
    existing_ids = vector_store.get()["ids"]
    if existing_ids:
        vector_store.delete(ids=existing_ids)

    if documents:
        vector_store.add_documents(documents)

    return len(documents)


def retrieve_relevant_context(query: str, k: int = 5) -> list[str]:
    """Find the k most relevant pieces of task/project text for a given query."""
    results = vector_store.similarity_search(query, k=k)
    return [doc.page_content for doc in results]
