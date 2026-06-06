"""Unit tests for the SQLite-backed expense MCP server.

Each test runs against a fresh, isolated database in a temp directory so the
real ``databases.db`` is never touched.
"""

import expense_server as es
import pytest


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Point the server at a throwaway database and initialise its schema."""
    monkeypatch.setattr(es, "DB_PATH", tmp_path / "test.db")
    es._init_db()
    return es


def test_add_expense_persists_and_normalises_category(db):
    result = db.add_expense(12.5, "  Food  ", "lunch")
    row = result["added"]
    assert row["amount"] == 12.5
    assert row["category"] == "food"  # trimmed + lowercased
    assert row["description"] == "lunch"


def test_add_expense_rejects_non_positive(db):
    assert "error" in db.add_expense(0, "food")
    assert "error" in db.add_expense(-5, "food")


def test_total_spent_filters_by_category(db):
    db.add_expense(10, "food")
    db.add_expense(15, "food")
    db.add_expense(40, "travel")
    assert db.total_spent()["total"] == 65
    assert db.total_spent(category="food")["total"] == 25


def test_list_expenses_orders_and_limits(db):
    for i in range(3):
        db.add_expense(i + 1, "food", date=f"2026-01-0{i + 1}")
    listed = db.list_expenses(limit=2)
    assert listed["count"] == 2
    assert len(listed["expenses"]) == 2


def test_summarize_by_category(db):
    db.add_expense(10, "food")
    db.add_expense(30, "travel")
    summary = {c["category"]: c["total"] for c in db.summarize_by_category()["categories"]}
    assert summary == {"food": 10, "travel": 30}


def test_update_expense_changes_only_given_fields(db):
    new_id = db.add_expense(10, "food", "snack")["added"]["id"]
    updated = db.update_expense(new_id, amount=20)["updated"]
    assert updated["amount"] == 20
    assert updated["category"] == "food"  # unchanged
    assert updated["description"] == "snack"  # unchanged


def test_delete_expense(db):
    new_id = db.add_expense(10, "food")["added"]["id"]
    assert db.delete_expense(new_id) == {"deleted_id": new_id}
    assert "error" in db.delete_expense(new_id)  # already gone
