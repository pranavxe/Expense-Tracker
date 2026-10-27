# Expense Tracker

A web-based expense tracker built with Flask, SQLite and Chart.js.

## Features
- Add, search, filter and delete expenses
- Dashboard with total, monthly spend, transaction count and top category
- Doughnut chart (by category) and bar chart (by month)
- Export all data to CSV
- Responsive dark UI
- Server-side validation and parameterized SQL queries

## Tech stack
- Backend: Python, Flask, SQLite
- Frontend: HTML, CSS, vanilla JavaScript, Chart.js

## Project structure
```
app.py          # routes and API
database.py     # all SQL code
templates/      # HTML
static/         # CSS and JavaScript
```

## Run locally
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:5000

## Future improvements
- Edit existing expenses
- Monthly budget limits with warnings
- User login
- Deploy online