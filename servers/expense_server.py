"""Expense-tracker MCP server.

A local Model Context Protocol (MCP) server backed by SQLite. It exposes six
tools (three write, three read) and persists to ``databases.db`` alongside this
file, so it behaves the same on a developer machine and on the cloud.

Launched over STDIO by the ``MultiServerMCPClient`` in ``mcp_config.py``.

Run standalone for a quick check::

    uv run fastmcp run servers/expense_server.py

Note: on Streamlit Community Cloud the filesystem is ephemeral, so the database
resets on restart. For durable cloud storage, point ``DB_PATH`` at a hosted
database (e.g. Postgres or Turso) instead of local SQLite.
"""

import sqlite3
from datetime import date as _date
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

# Database lives next to this script -> portable (local + cloud).
DB_PATH = Path(__file__).resolve().parent / "databases.db"

mcp = FastMCP(name="ExpenseTracker")


def _connect() -> sqlite3.Connection:
    """Open a fresh connection per call (safe across MCP worker threads)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    """Create the expenses table if it doesn't exist yet."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL
            )
            """
        )
        conn.commit()


_init_db()


# ─────────────────────────────────────────────────────────────────────────
# WRITE tools
# ─────────────────────────────────────────────────────────────────────────
@mcp.tool
def add_expense(
    amount: float,
    category: str,
    description: str = "",
    date: str = "",
) -> dict:
    """Add a new expense and return the stored row.

    amount: cost (e.g. 12.50). category: e.g. 'food', 'travel'.
    description: optional note. date: 'YYYY-MM-DD' (defaults to today).
    """
    if amount <= 0:
        return {"error": "amount must be positive"}
    if not date:
        date = _date.today().isoformat()
    created_at = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (date, amount, category, description, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (date, float(amount), category.strip().lower(), description, created_at),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (new_id,)).fetchone()
    return {"added": dict(row)}


@mcp.tool
def delete_expense(expense_id: int) -> dict:
    """Delete the expense with the given id."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
    if cur.rowcount == 0:
        return {"error": f"no expense with id {expense_id}"}
    return {"deleted_id": expense_id}


@mcp.tool
def update_expense(
    expense_id: int,
    amount: float = -1.0,
    category: str = "",
    description: str = "",
    date: str = "",
) -> dict:
    """Update fields of an existing expense. Only non-empty fields are changed."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if row is None:
            return {"error": f"no expense with id {expense_id}"}
        new_amount = float(amount) if amount > 0 else row["amount"]
        new_cat = category.strip().lower() if category else row["category"]
        new_desc = description if description else row["description"]
        new_date = date if date else row["date"]
        conn.execute(
            "UPDATE expenses SET amount=?, category=?, description=?, date=? WHERE id=?",
            (new_amount, new_cat, new_desc, new_date, expense_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    return {"updated": dict(updated)}


# ─────────────────────────────────────────────────────────────────────────
# READ tools
# ─────────────────────────────────────────────────────────────────────────
@mcp.tool
def list_expenses(category: str = "", limit: int = 50) -> dict:
    """List recent expenses, optionally filtered by category (most recent first)."""
    with _connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM expenses WHERE category = ? ORDER BY date DESC, id DESC LIMIT ?",
                (category.strip().lower(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM expenses ORDER BY date DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return {"count": len(rows), "expenses": [dict(r) for r in rows]}


@mcp.tool
def total_spent(category: str = "", since: str = "") -> dict:
    """Total amount spent, optionally filtered by category and/or a start date.

    since: 'YYYY-MM-DD' — include expenses on/after this date.
    """
    query = "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n FROM expenses WHERE 1=1"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category.strip().lower())
    if since:
        query += " AND date >= ?"
        params.append(since)
    with _connect() as conn:
        row = conn.execute(query, params).fetchone()
    return {"total": round(row["total"], 2), "count": row["n"]}


@mcp.tool
def summarize_by_category() -> dict:
    """Summarize spending grouped by category (total and count per category)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT category, ROUND(SUM(amount), 2) AS total, COUNT(*) AS n "
            "FROM expenses GROUP BY category ORDER BY total DESC"
        ).fetchall()
    return {"categories": [dict(r) for r in rows]}


if __name__ == "__main__":
    mcp.run()  # STDIO transport
