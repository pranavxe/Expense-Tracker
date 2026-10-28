
"""Expense Tracker with registration, login, and private user expenses."""

import csv
import io
import math
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from hmac import compare_digest

from flask import (
    Flask,
    Response,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import auth_database as db


app = Flask(__name__)

# Keep the secret outside the source code and Git repository.
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. Set it in PowerShell before starting Flask."
    )

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

db.init_db()


def csrf_token():
    """Return a token used to protect forms and API requests."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def prepare_request():
    """Load the signed-in user and check CSRF tokens."""
    user_id = session.get("user_id")
    g.user = db.get_user_by_id(user_id) if user_id is not None else None

    if user_id is not None and g.user is None:
        session.clear()

    # All state-changing requests must provide a valid CSRF token.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("_csrf_token", "")
        supplied = (
            request.form.get("csrf_token", "")
            or request.headers.get("X-CSRF-Token", "")
        )

        if not expected or not supplied or not compare_digest(expected, supplied):
            if request.path.startswith("/api/"):
                return jsonify(error="Invalid or missing security token. Refresh and try again."), 400
            abort(400, description="Invalid or missing security token. Refresh and try again.")


def login_required(view):
    """Require an authenticated user for a route."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="Please log in to continue."), 401
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
@login_required
def index():
    return render_template("index.html", user=g.user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or len(name) > 80:
        return render_template(
            "register.html", error="Enter a name of 1 to 80 characters."
        ), 400

    if (
        not email
        or len(email) > 254
        or "@" not in email
        or email.startswith("@")
        or email.endswith("@")
    ):
        return render_template(
            "register.html", error="Enter a valid email address."
        ), 400

    if len(password) < 8:
        return render_template(
            "register.html", error="Password must contain at least 8 characters."
        ), 400

    if len(password) > 128:
        return render_template(
            "register.html", error="Password must be 128 characters or fewer."
        ), 400

    if password != confirm_password:
        return render_template(
            "register.html", error="The passwords do not match."
        ), 400

    try:
        password_hash = generate_password_hash(password)
        user_id = db.create_user(name, email, password_hash)
    except Exception as exc:
        # SQLite reports duplicate emails as an integrity error.
        import sqlite3

        if isinstance(exc, sqlite3.IntegrityError):
            return render_template(
                "register.html", error="An account with that email already exists."
            ), 409
        raise

    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    session.permanent = True

    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = db.get_user_by_email(email) if email else None

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error="Invalid email or password."
        ), 401

    # Clear old session data to prevent session fixation.
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session.permanent = True

    return redirect(url_for("index"))


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/api/expenses")
@login_required
def list_expenses():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    return jsonify(db.get_expenses(g.user["id"], search, category))


@app.post("/api/expenses")
@login_required
def create_expense():
    data = request.get_json(silent=True) or {}

    try:
        date = datetime.strptime(
            data.get("date", ""), "%Y-%m-%d"
        ).strftime("%Y-%m-%d")
        amount = float(data.get("amount"))
    except (ValueError, TypeError):
        return jsonify(error="Please enter a valid date and amount."), 400

    if not math.isfinite(amount) or amount <= 0:
        return jsonify(error="Amount must be a valid number greater than 0."), 400

    raw_category = data.get("category") or "Other"
    raw_description = data.get("description") or ""

    if not isinstance(raw_category, str) or not isinstance(raw_description, str):
        return jsonify(error="Category and description must be text."), 400

    category = raw_category.strip().title()[:30] or "Other"
    description = raw_description.strip()[:100]

    new_id = db.add_expense(
        g.user["id"], date, category, description, round(amount, 2)
    )
    return jsonify(id=new_id), 201


@app.delete("/api/expenses/<int:expense_id>")
@login_required
def remove_expense(expense_id):
    # The database checks both the expense ID and its owner.
    if db.delete_expense(expense_id, g.user["id"]):
        return jsonify(ok=True)

    return jsonify(error="Expense not found."), 404


@app.get("/api/summary")
@login_required
def summary():
    return jsonify(db.get_summary(g.user["id"]))


@app.get("/export")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Category", "Description", "Amount"])

    for expense in db.get_expenses(g.user["id"]):
        writer.writerow([
            expense["id"],
            expense["date"],
            expense["category"],
            expense["description"],
            expense["amount"],
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=expenses.csv"
        },
    )


if __name__ == "__main__":
    app.run(debug=True)
