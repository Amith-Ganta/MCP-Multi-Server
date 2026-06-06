# MCP Chat — multi-server assistant

A Streamlit chat UI ([app.py](app.py)) that talks to several MCP servers
through one OpenAI model:

| Server          | Type                | Runs where           |
|-----------------|---------------------|----------------------|
| `math`          | local STDIO         | anywhere (portable)  |
| `expense`       | local STDIO + SQLite| anywhere (reads/writes `databases.db`) |
| `manim-server`  | local STDIO         | Windows only         |

Each server connects **independently** — if one fails (missing token, Windows-only,
offline), it is shown as failed in the sidebar and skipped, so the app keeps working.

## Project layout

```
MCP-CLient/
├── mcp_config.py        # shared: TLS, secrets, server registry, connector
├── app.py               # Streamlit chat UI            (uv run streamlit run app.py)
├── cli.py               # command-line client          (uv run python cli.py)
├── math_server.py       # FastMCP math server (18 tools)
├── expense_server.py    # FastMCP expense tracker (6 tools, SQLite)
├── databases.db         # SQLite store (auto-created, git-ignored)
├── pyproject.toml       # project metadata + dependencies (uv)
├── requirements.txt     # pip mirror of deps (for Streamlit Cloud)
└── .streamlit/
    └── secrets.toml.example
```

Both entry points share [mcp_config.py](mcp_config.py), so server paths, secret
loading, and the connection logic are defined in exactly one place. The expense
server exposes: `add_expense`, `delete_expense`, `update_expense`,
`list_expenses`, `total_spent`, `summarize_by_category`.

## Run locally

```bash
uv sync --native-tls
uv run streamlit run app.py         # web UI
uv run python cli.py                # CLI, or pass a prompt:
uv run python cli.py "What is 12 factorial?"
```

Secrets come from `.env` (or `.streamlit/secrets.toml`):

```
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o          # optional
```

The expense server is local (SQLite) and needs no token.

## Deploy to Streamlit Community Cloud

1. Push this folder to GitHub (the real `.env` / `secrets.toml` stay ignored).
2. Create a new app at <https://share.streamlit.io>, pointing at `app.py`.
3. In **App settings → Secrets**, paste the keys from
   [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example) with real values.
4. Deploy. The `math` and `expense` servers will work; the Windows-only
   `manim-server` is automatically skipped on the Linux cloud.

> **Note:** Streamlit Community Cloud has an ephemeral filesystem, so
> `databases.db` resets when the app restarts. That's fine for a demo; for
> durable storage on the cloud, point `expense_server.py` at a hosted database
> (e.g. Postgres/Turso) instead of local SQLite.

## Notes

- Local servers launch with the **current Python interpreter**
  (`sys.executable`), so they need no `uv` on the cloud — the packages in
  `requirements.txt` are enough.
- TLS verification is routed through the OS certificate store via `truststore`
  (`mcp_config.py`), which keeps HTTPS working both behind a corporate proxy and
  on the cloud.
