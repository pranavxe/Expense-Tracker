"""Expense Tracker - Flask web app."""

import csv
import io
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request

import database as db

app = Flask(__name__)
db.init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/expenses")
def list_expenses():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    return jsonify(db.get_expenses(search, category))


@app.post("/api/expenses")
def create_expense():
    data = request.get_json(silent=True) or {}

    try:
        date = datetime.strptime(data.get("date", ""), "%Y-%m-%d").strftime("%Y-%m-%d")
        amount = float(data.get("amount"))
    except (ValueError, TypeError):
        return jsonify(error="Please enter a valid date and amount."), 400

    if amount <= 0:
        return jsonify(error="Amount must be greater than 0."), 400

    category = (data.get("category") or "Other").strip().title()[:30] or "Other"
    description = (data.get("description") or "").strip()[:100]

    new_id = db.add_expense(date, category, description, round(amount, 2))
    return jsonify(id=new_id), 201


@app.delete("/api/expenses/<int:expense_id>")
def remove_expense(expense_id):
    if db.delete_expense(expense_id):
        return jsonify(ok=True)
    return jsonify(error="Expense not found."), 404


@app.get("/api/summary")
def summary():
    return jsonify(db.get_summary())


@app.get("/export")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Category", "Description", "Amount"])
    for e in db.get_expenses():
        writer.writerow([e["id"], e["date"], e["category"], e["description"], e["amount"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True)