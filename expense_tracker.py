"""Expense Tracker - a simple CLI app using Python and SQLite."""

import csv
import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_FILE = Path(__file__).with_name("expenses.db")


def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL
            )"""
        )


def read_amount(prompt):
    while True:
        try:
            value = float(input(prompt))
            if value <= 0:
                print("Amount must be greater than 0.")
                continue
            return value
        except ValueError:
            print("Please enter a valid number.")


def read_date(prompt):
    while True:
        text = input(prompt).strip()
        if text == "":
            return date.today().isoformat()
        try:
            datetime.strptime(text, "%Y-%m-%d")
            return text
        except ValueError:
            print("Use the format YYYY-MM-DD (or press Enter for today).")


def add_expense():
    print("\n--- Add Expense ---")
    exp_date = read_date("Date (YYYY-MM-DD, Enter = today): ")
    category = input("Category (e.g. Food, Travel, Books): ").strip().title() or "Other"
    description = input("Description: ").strip()
    amount = read_amount("Amount: ")

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            (exp_date, category, description, amount),
        )
    print("Expense added!")


def view_expenses():
    print("\n--- All Expenses ---")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, date, category, description, amount FROM expenses ORDER BY date DESC, id DESC"
        ).fetchall()

    if not rows:
        print("No expenses recorded yet.")
        return

    print(f"{'ID':<5}{'Date':<12}{'Category':<14}{'Description':<22}{'Amount':>10}")
    print("-" * 63)
    for id_, d, cat, desc, amt in rows:
        print(f"{id_:<5}{d:<12}{cat:<14}{desc[:20]:<22}{amt:>10.2f}")
    print("-" * 63)
    print(f"{'Total':<53}{sum(r[4] for r in rows):>10.2f}")


def delete_expense():
    view_expenses()
    try:
        expense_id = int(input("\nEnter the ID to delete (0 to cancel): "))
    except ValueError:
        print("Invalid ID.")
        return
    if expense_id == 0:
        return

    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    print("Deleted." if cursor.rowcount else "No expense with that ID.")


def category_summary():
    print("\n--- Spending by Category ---")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category, SUM(amount) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC"
        ).fetchall()

    if not rows:
        print("No data yet.")
        return

    total = sum(r[1] for r in rows)
    for category, amount in rows:
        percent = amount / total * 100
        bar = "#" * int(percent / 5)
        print(f"{category:<14}{amount:>10.2f}  {percent:5.1f}%  {bar}")


def monthly_summary():
    print("\n--- Spending by Month ---")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT substr(date, 1, 7) AS month, SUM(amount) FROM expenses "
            "GROUP BY month ORDER BY month DESC"
        ).fetchall()

    if not rows:
        print("No data yet.")
        return
    for month, amount in rows:
        print(f"{month}   {amount:>10.2f}")


def export_csv():
    filename = Path(__file__).with_name("expenses_export.csv")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, date, category, description, amount FROM expenses ORDER BY date"
        ).fetchall()

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Date", "Category", "Description", "Amount"])
        writer.writerows(rows)
    print(f"Exported {len(rows)} expenses to {filename.name}")


def main():
    init_db()
    actions = {
        "1": ("Add expense", add_expense),
        "2": ("View all expenses", view_expenses),
        "3": ("Delete an expense", delete_expense),
        "4": ("Summary by category", category_summary),
        "5": ("Summary by month", monthly_summary),
        "6": ("Export to CSV", export_csv),
    }

    while True:
        print("\n===== EXPENSE TRACKER =====")
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print("0. Exit")

        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        action = actions.get(choice)
        if action:
            action[1]()
        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()