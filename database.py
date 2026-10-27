"""Database layer: all SQLite code lives here."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses.db"


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL
            )"""
        )


def add_expense(date, category, description, amount):
    with db() as conn:
        cursor = conn.execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            (date, category, description, amount),
        )
        return cursor.lastrowid


def get_expenses(search="", category=""):
    query = "SELECT id, date, category, description, amount FROM expenses WHERE 1=1"
    params = []
    if search:
        query += " AND (description LIKE ? OR category LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY date DESC, id DESC"

    with db() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def delete_expense(expense_id):
    with db() as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return cursor.rowcount > 0


def get_summary():
    with db() as conn:
        total, count = conn.execute(
            "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM expenses"
        ).fetchone()

        this_month = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses "
            "WHERE substr(date, 1, 7) = strftime('%Y-%m', 'now', 'localtime')"
        ).fetchone()[0]

        categories = [
            dict(row)
            for row in conn.execute(
                "SELECT category, ROUND(SUM(amount), 2) AS total FROM expenses "
                "GROUP BY category ORDER BY total DESC"
            )
        ]

        months = [
            dict(row)
            for row in conn.execute(
                "SELECT substr(date, 1, 7) AS month, ROUND(SUM(amount), 2) AS total "
                "FROM expenses GROUP BY month ORDER BY month"
            )
        ]

    return {
        "total": round(total, 2),
        "count": count,
        "this_month": round(this_month, 2),
        "top_category": categories[0]["category"] if categories else "-",
        "categories": categories,
        "months": months,
    }