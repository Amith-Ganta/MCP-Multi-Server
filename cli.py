"""Command-line MCP client.

Connects to the local MCP servers defined in :mod:`mcp_config`, binds their
tools to an OpenAI chat model, runs a single prompt through one tool-calling
round trip, and prints the answer. Use ``app.py`` for the interactive web UI.

    uv run python cli.py
    uv run python cli.py "What is 12 factorial?"
"""

from __future__ import annotations

import asyncio
import json
import sys

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from mcp_config import (
    SYSTEM_PROMPT,
    build_servers,
    connect_tools,
    get_model,
    get_secret,
)

DEFAULT_PROMPT = (
    "What is the factorial of 6, and the greatest common divisor of 48 and 18? "
    "Use the math tools."
)


async def answer(prompt: str) -> str:
    """Run one prompt through the tool-calling loop and return the final text."""
    if not get_secret("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set (add it to .env).")

    tools, statuses = await connect_tools(build_servers())
    for name, status in statuses.items():
        detail = f"{status['tools']} tools" if status["ok"] else status["detail"]
        print(f"  [{'ok' if status['ok'] else 'ERR'}] {name}: {detail}")
    if not tools:
        raise SystemExit("No MCP tools available; cannot continue.")

    tools_by_name = {tool.name: tool for tool in tools}
    llm = ChatOpenAI(model=get_model())
    llm_with_tools = llm.bind_tools(tools)

    history = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
    response = await llm_with_tools.ainvoke(history)

    if not getattr(response, "tool_calls", None):
        return response.content or ""

    history.append(response)
    for call in response.tool_calls:
        tool = tools_by_name.get(call["name"])
        result = (
            await tool.ainvoke(call.get("args") or {})
            if tool is not None
            else f"Tool '{call['name']}' is not available."
        )
        history.append(
            ToolMessage(tool_call_id=call["id"], content=json.dumps(result, default=str))
        )

    final = await llm.ainvoke(history)
    return final.content or ""


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or DEFAULT_PROMPT
    print(f"Prompt: {prompt}\nConnecting to MCP servers…")
    print(f"\nAnswer:\n{asyncio.run(answer(prompt))}")


if __name__ == "__main__":
    main()
