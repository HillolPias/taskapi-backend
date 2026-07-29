from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.llm import llm
from app.schemas import ChatRequest, ChatResponse
from app.rag import build_index, retrieve_relevant_context
from app.agent import run_agent
from app.agent_graph import run_agent_graph

router = APIRouter(prefix="/chat", tags=["chat"])


def extract_text(content) -> str:
    """Gemini/LangChain responses can be a plain string or a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = await llm.ainvoke(request.message)
    return ChatResponse(reply=extract_text(response.content))


@router.post("/reindex")
async def reindex(db: AsyncSession = Depends(get_db)):
    count = await build_index(db)
    return {"indexed_documents": count}


@router.post("/rag", response_model=ChatResponse)
async def rag_chat(request: ChatRequest):
    context_chunks = retrieve_relevant_context(request.message)
    context_text = "\n".join(f"- {chunk}" for chunk in context_chunks)

    prompt = f"""Answer the user's question using ONLY the context below. If the context doesn't contain the answer, say you don't have that information.

Context:
{context_text}

Question: {request.message}"""

    response = await llm.ainvoke(prompt)
    return ChatResponse(reply=extract_text(response.content))


@router.post("/agent", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    reply = await run_agent(request.message)
    return ChatResponse(reply=reply)


@router.post("/graph", response_model=ChatResponse)
async def graph_chat(request: ChatRequest):
    reply = await run_agent_graph(request.message)
    return ChatResponse(reply=reply)
