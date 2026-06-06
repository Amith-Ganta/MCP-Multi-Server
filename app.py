"""Streamlit chat front end for the MCP servers.

A single OpenAI assistant backed by several MCP servers: a local math server, a
local SQLite-backed expense tracker, and an optional Windows-only Manim server.
Server discovery, secrets, and connection logic live in :mod:`mcp_config`.

    uv run streamlit run app.py

Designed to be cloud-deployable (e.g. Streamlit Community Cloud): local servers
launch with the current interpreter, and each server connects independently so
one failure is surfaced and skipped rather than crashing the whole app.
"""

from __future__ import annotations

import asyncio
import json

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from mcp_config import (
    SYSTEM_PROMPT,
    build_servers,
    connect_tools,
    get_model,
    get_secret,
)

MODEL = get_model()


# --------------------------------------------------------------------------
# Async helper — reuse one event loop across Streamlit reruns
# --------------------------------------------------------------------------
def get_loop() -> asyncio.AbstractEventLoop:
    loop = st.session_state.get("_loop")
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        st.session_state["_loop"] = loop
    return loop


def run_async(coro):
    """Run a coroutine on the session's persistent event loop."""
    return get_loop().run_until_complete(coro)


# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(page_title="MCP Chat", page_icon="🧰", layout="wide")
st.title("🧰 MCP Chat")
st.caption("One assistant, many MCP servers — math · expenses · animation")


def initialize() -> None:
    """One-time setup: LLM, MCP tools, and conversation state."""
    if not get_secret("OPENAI_API_KEY"):
        st.error("`OPENAI_API_KEY` is not set. Add it to `.env` or Streamlit secrets.")
        st.stop()

    servers = build_servers()
    if not servers:
        st.error("No MCP servers are available in this environment.")
        st.stop()

    with st.spinner("Connecting to MCP servers…"):
        tools, statuses = run_async(connect_tools(servers))

    llm = ChatOpenAI(model=MODEL)
    st.session_state.llm = llm
    st.session_state.llm_with_tools = llm.bind_tools(tools)
    st.session_state.tools = tools
    st.session_state.tool_by_name = {tool.name: tool for tool in tools}
    st.session_state.server_status = statuses
    st.session_state.history = [SystemMessage(content=SYSTEM_PROMPT)]
    st.session_state.initialized = True


if "initialized" not in st.session_state:
    initialize()


# --------------------------------------------------------------------------
# Sidebar — connection status, tool inventory, controls
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Connections")
    st.write(f"**Model:** `{MODEL}`")
    for name, status in st.session_state.server_status.items():
        if status["ok"]:
            st.write(f"✅ **{name}** — {status['tools']} tools")
        else:
            st.write(f"❌ **{name}** — {status['detail']}")

    st.divider()
    st.subheader(f"🛠️ Tools ({len(st.session_state.tools)})")
    with st.expander("Show all tools", expanded=False):
        for tool in sorted(st.session_state.tools, key=lambda t: t.name):
            st.markdown(f"- `{tool.name}`")

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.history = [SystemMessage(content=SYSTEM_PROMPT)]
        st.rerun()
    if st.button("🔄 Reconnect servers", use_container_width=True):
        st.session_state.pop("initialized", None)
        st.rerun()


# --------------------------------------------------------------------------
# Render chat history (skip system + tool messages; hide intermediate AI)
# --------------------------------------------------------------------------
for message in st.session_state.history:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
        with st.chat_message("assistant"):
            st.markdown(message.content)


# --------------------------------------------------------------------------
# Tool execution
# --------------------------------------------------------------------------
def run_tool_calls(tool_calls: list) -> list[tuple[str, dict, object]]:
    """Execute the model's requested tool calls, recording each invocation."""
    call_log: list[tuple[str, dict, object]] = []
    tool_messages: list[ToolMessage] = []
    for call in tool_calls:
        name = call["name"]
        args = call.get("args") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                pass
        tool = st.session_state.tool_by_name.get(name)
        result = (
            run_async(tool.ainvoke(args))
            if tool is not None
            else f"Tool '{name}' is not available."
        )
        call_log.append((name, args, result))
        tool_messages.append(
            ToolMessage(tool_call_id=call["id"], content=json.dumps(result, default=str))
        )
    st.session_state.history.extend(tool_messages)
    return call_log


# --------------------------------------------------------------------------
# Chat input + agent loop
# --------------------------------------------------------------------------
user_text = st.chat_input("Ask about math, expenses, or animations…")
if user_text:
    with st.chat_message("user"):
        st.markdown(user_text)
    st.session_state.history.append(HumanMessage(content=user_text))

    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                first = run_async(
                    st.session_state.llm_with_tools.ainvoke(st.session_state.history)
                )

            if not getattr(first, "tool_calls", None):
                st.markdown(first.content or "")
                st.session_state.history.append(first)
            else:
                # Keep the assistant tool-call message (not rendered), run the
                # tools, then compose a final answer from their results.
                st.session_state.history.append(first)

                with st.spinner(f"Running {len(first.tool_calls)} tool(s)…"):
                    call_log = run_tool_calls(first.tool_calls)

                with st.expander("🔧 Tool calls", expanded=False):
                    for name, args, result in call_log:
                        st.markdown(f"**`{name}`** · args: `{args}`")
                        st.code(json.dumps(result, indent=2, default=str), language="json")

                with st.spinner("Composing answer…"):
                    final = run_async(st.session_state.llm.ainvoke(st.session_state.history))
                st.markdown(final.content or "")
                st.session_state.history.append(AIMessage(content=final.content or ""))
    except Exception as exc:  # noqa: BLE001 - surface any runtime failure to the user
        st.error(f"Something went wrong: {type(exc).__name__}: {exc}")
