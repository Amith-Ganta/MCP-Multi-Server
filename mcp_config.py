"""Shared configuration and helpers for the MCP chat clients.

Both entry points — the command-line client (``cli.py``) and the Streamlit app
(``app.py``) — rely on this module for TLS setup, secret loading, the MCP server
registry, and a fault-tolerant multi-server connector. Centralising it here
keeps server paths and connection logic defined in exactly one place.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Route TLS verification through the operating system's certificate store so
# that HTTPS calls (e.g. the OpenAI API) succeed both behind a corporate
# TLS-interception proxy and on managed cloud hosts. Must run before any TLS
# connection is opened, hence the early, best-effort injection.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:  # pragma: no cover - truststore is an optional safety net
    pass

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
SERVERS_DIR = PROJECT_ROOT / "servers"
MATH_SERVER = SERVERS_DIR / "math_server.py"
EXPENSE_SERVER = SERVERS_DIR / "expense_server.py"

# Windows-only Manim server (mirrors the local Claude Desktop configuration).
MANIM_PYTHON = Path(r"C:\Users\HP\manim-env\Scripts\python.exe")
MANIM_SERVER = Path(r"C:\Users\HP\Desktop\manim-mcp-server\src\manim_server.py")
MANIM_EXECUTABLE = Path(r"C:\Users\HP\manim-env\Scripts\manim.exe")

# --------------------------------------------------------------------------
# Model and prompt
# --------------------------------------------------------------------------
DEFAULT_MODEL = "gpt-4o"

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to math, expense-tracking, and "
    "animation tools. Do not narrate status updates while calling tools. Once "
    "the tools have run, return a single concise, well-formatted answer."
)


def get_secret(name: str, default: str = "") -> str:
    """Return a secret from the environment first, then Streamlit secrets.

    Streamlit is imported lazily so the command-line client does not pay for it.
    """
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets[name]
    except Exception:
        return default


def get_model() -> str:
    """Return the chat model name, overridable via the ``OPENAI_MODEL`` secret."""
    return get_secret("OPENAI_MODEL", DEFAULT_MODEL)


def build_servers() -> dict[str, dict]:
    """Return the MCP server registry, including only servers runnable here.

    Local servers launch with the current interpreter (``sys.executable``) so
    they behave identically on a developer machine and in the cloud. The
    Windows-only Manim server is included solely when its files are present.
    """
    servers: dict[str, dict] = {}

    if MATH_SERVER.exists():
        servers["math"] = {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(MATH_SERVER)],
        }

    if EXPENSE_SERVER.exists():
        servers["expense"] = {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(EXPENSE_SERVER)],
        }

    if os.name == "nt" and MANIM_SERVER.exists() and MANIM_PYTHON.exists():
        servers["manim-server"] = {
            "transport": "stdio",
            "command": str(MANIM_PYTHON),
            "args": [str(MANIM_SERVER)],
            "env": {"MANIM_EXECUTABLE": str(MANIM_EXECUTABLE)},
        }

    return servers


async def connect_tools(servers: dict[str, dict]) -> tuple[list, dict[str, dict]]:
    """Connect to each server independently so one failure cannot break the rest.

    Returns ``(tools, statuses)`` where ``statuses`` maps each server name to a
    small dict: ``{"ok": bool, "tools": int, "detail": str}``.
    """
    tools: list = []
    statuses: dict[str, dict] = {}
    for name, config in servers.items():
        try:
            client = MultiServerMCPClient({name: config})
            server_tools = await client.get_tools()
            tools.extend(server_tools)
            statuses[name] = {"ok": True, "tools": len(server_tools), "detail": ""}
        except Exception as exc:  # noqa: BLE001 - report any connection failure
            statuses[name] = {
                "ok": False,
                "tools": 0,
                "detail": f"{type(exc).__name__}: {exc}",
            }
    return tools, statuses
