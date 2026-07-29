from langchain_core.messages import HumanMessage, ToolMessage

from app.agent_tools import tools
from app.llm import llm

llm_with_tools = llm.bind_tools(tools)

tools_by_name = {t.name: t for t in tools}


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


async def run_agent(user_message: str, max_steps: int = 5) -> str:
    messages = [HumanMessage(content=user_message)]

    for _ in range(max_steps):
        ai_message = await llm_with_tools.ainvoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            # No more tools to call — this is the final answer
            return extract_text(ai_message.content)

        # The LLM asked to call one or more tools — actually run them
        for call in ai_message.tool_calls:
            tool_fn = tools_by_name[call["name"]]
            result = await tool_fn.ainvoke(call["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return "I couldn't complete the request within the allowed steps."
