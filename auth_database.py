
"""Database layer for the authenticated Expense Tracker."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses_auth.db"


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the fresh authentication and expense tables."""
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL CHECK (amount > 0),
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )


def create_user(name, email, password_hash):
    """Create a user; return their ID."""
    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (name, email, password_hash),
        )
        return cursor.lastrowid


def get_user_by_email(email):
    """Find a user by email, ignoring email letter case."""
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id):
    """Find a user by their ID."""
    with db() as conn:
        row = conn.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def add_expense(user_id, date, category, description, amount):
    """Add an expense belonging to one specific user."""
    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses
                (user_id, date, category, description, amount)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, date, category, description, amount),
        )
        return cursor.lastrowid


def get_expenses(user_id, search="", category=""):
    """Return only the selected user's expenses."""
    query = """
        SELECT id, date, category, description, amount
        FROM expenses
        WHERE user_id = ?
    """
    params = [user_id]

    if search:
        query += " AND (description LIKE ? OR category LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY date DESC, id DESC"

    with db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def delete_expense(expense_id, user_id):
    """Delete an expense only if it belongs to this user."""
    with db() as conn:
        cursor = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        return cursor.rowcount > 0


def get_summary(user_id):
    """Calculate dashboard totals for one user only."""
    with db() as conn:
        total, count = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0), COUNT(*)
            FROM expenses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        this_month = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE user_id = ?
              AND substr(date, 1, 7) =
                  strftime('%Y-%m', 'now', 'localtime')
            """,
            (user_id,),
        ).fetchone()[0]

        categories = [
            dict(row)
            for row in conn.execute(
                """
                SELECT category, ROUND(SUM(amount), 2) AS total
                FROM expenses
                WHERE user_id = ?
                GROUP BY category
                ORDER BY total DESC
                """,
                (user_id,),
            )
        ]

        months = [
            dict(row)
            for row in conn.execute(
                """
                SELECT substr(date, 1, 7) AS month,
                       ROUND(SUM(amount), 2) AS total
                FROM expenses
                WHERE user_id = ?
                GROUP BY month
                ORDER BY month
                """,
                (user_id,),
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
