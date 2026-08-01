from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import ToolMessage, HumanMessage

from app.agent_tools import tools
from app.llm import llm

llm_with_tools = llm.bind_tools(tools)
tools_by_name = {t.name: t for t in tools}


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


async def reason(state: AgentState) -> dict:
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


async def act(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    tool_messages = []
    for call in last_message.tool_calls:
        tool_fn = tools_by_name[call["name"]]
        result = await tool_fn.ainvoke(call["args"])
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return {"messages": tool_messages}


def route_after_reasoning(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "act"
    return END


graph_builder = StateGraph(AgentState)
graph_builder.add_node("reason", reason)
graph_builder.add_node("act", act)
graph_builder.set_entry_point("reason")
graph_builder.add_conditional_edges(
    "reason",
    route_after_reasoning,
    {"act": "act", END: END},
)
graph_builder.add_edge("act", "reason")

agent_graph = graph_builder.compile()


def extract_text(content) -> str:
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


async def run_agent_graph(user_message: str) -> str:
    result = await agent_graph.ainvoke(
        {"messages": [HumanMessage(content=user_message)]}
    )
    final_message = result["messages"][-1]
    return extract_text(final_message.content)


async def stream_agent_graph(user_message: str):
    async for event in agent_graph.astream_events(
        {"messages": [HumanMessage(content=user_message)]}, version="v2"
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = extract_text(chunk.content)
            if text:
                yield text
        elif kind == "on_tool_start":
            tool_name = event["name"]
            yield f"\n\n_🔧 using {tool_name}..._\n\n"
