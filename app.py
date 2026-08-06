import sqlite3
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_expenses_for_user,
    get_category_breakdown_for_user,
    init_db,
    seed_db,
)

app = Flask(__name__)

# Required for flash() and session. Hardcoded dev key — replace before deploying.
app.secret_key = "dev-secret-change-me"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # If already signed in, the auth pages have nothing to offer.
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        form = {"name": name, "email": email}

        # ---- validation ----
        if not name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template("register.html", form=form)

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html", form=form)

        # ---- insert ----
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html", form=form)

        flash("Account created — please sign in.", "success")
        return redirect(url_for("login"))

    # GET
    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    # If already signed in, the auth pages have nothing to offer.
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        form = {"email": email}

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html", form=form)

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            # Same message either way — no user enumeration.
            flash("Invalid email or password.", "error")
            return render_template("login.html", form=form)

        # Success — establish session.
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        # flash(f"Welcome back, {user['name']}.", "success")
        return redirect(url_for("profile"))

    return render_template("login.html", form={})


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "success")
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Transaction history formatting                                      #
# ------------------------------------------------------------------ #

def format_tx_date(date_str):
    """Format a YYYY-MM-DD date string as 'DD MMM YYYY' (e.g. '12 Aug 2026')."""
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y")


def format_inr(amount):
    """Render a numeric amount as '₹1,234.50' — INR with thousands separators."""
    return f"₹{amount:,.2f}"


def build_transactions(expense_rows):
    """Convert a list of expense rows into the dicts the template renders.

    Each output dict has: date, description, category, amount_label.
    `description` is coerced to empty string when NULL.
    """
    return [
        {
            "date": format_tx_date(row["date"]),
            "description": row["description"] or "",
            "category": row["category"],
            "amount_label": format_inr(row["amount"]),
        }
        for row in expense_rows
    ]


# ------------------------------------------------------------------ #
# Summary stats formatting                                            #
# ------------------------------------------------------------------ #

def build_stats(expense_rows, breakdown_rows):
    """Compute total_spent, transaction_count, top_category for the stats row.

    `expense_rows` is the full expense list (used for totals + count).
    `breakdown_rows` is the category-breakdown result (used for top_category
    by reading its first row, which is already ordered by total DESC).
    Returns a dict matching the keys profile.html reads on `stats.*`.
    """
    total_spent = sum((row["amount"] for row in expense_rows), 0.0)
    transaction_count = len(expense_rows)
    top_category = breakdown_rows[0]["category"] if breakdown_rows else "—"

    return {
        "total_spent": total_spent,
        "total_spent_label": format_inr(total_spent),
        "transaction_count": transaction_count,
        "top_category": top_category,
    }


# ------------------------------------------------------------------ #
# Category breakdown formatting                                       #
# ------------------------------------------------------------------ #

def build_categories(breakdown_rows):
    """Convert category breakdown rows into the dicts the template iterates.

    Each output dict has: name, total, total_label, share (integer percent).
    When the breakdown is empty the helper returns [] — the template iterates
    safely over an empty list and the parent route passes it through.
    """
    if not breakdown_rows:
        return []

    overall_total = sum(row["total"] for row in breakdown_rows)
    if overall_total == 0:
        # All zero-amount expenses — guard against division by zero.
        return [
            {
                "name": row["category"],
                "total": row["total"],
                "total_label": format_inr(row["total"]),
                "share": 0,
            }
            for row in breakdown_rows
        ]

    return [
        {
            "name": row["category"],
            "total": row["total"],
            "total_label": format_inr(row["total"]),
            "share": round(row["total"] / overall_total * 100),
        }
        for row in breakdown_rows
    ]


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Session may outlive the user row (account deleted, DB reset).
    # Clear it and bounce to login instead of 500-ing.
    user_row = get_user_by_id(user_id)
    if user_row is None:
        session.clear()
        flash("Your session has expired. Please sign in again.", "error")
        return redirect(url_for("login"))

    # ---- date filter (Step 06) ----
    from database.filters import PRESETS, resolve_filter
    raw_args = {
        "range": request.args.get("range"),
        "start": request.args.get("start"),
        "end": request.args.get("end"),
    }
    flt = resolve_filter(raw_args)
    preset_keys = list(PRESETS.keys())  # template iterates to render <option>s

    expenses = get_expenses_for_user(
        user_id, start_date=flt["start"], end_date=flt["end"]
    )                                                # full filtered history
    recent = get_expenses_for_user(
        user_id, limit=20, start_date=flt["start"], end_date=flt["end"]
    )                                                # table shows the 20 newest
    breakdown = get_category_breakdown_for_user(
        user_id, start_date=flt["start"], end_date=flt["end"]
    )

    user = {
        "name": user_row["name"],
        "email": user_row["email"],
        "member_since": datetime.strptime(
            user_row["created_at"][:10], "%Y-%m-%d"
        ).strftime("%B %Y"),
        "initials": "".join(
            part[0] for part in user_row["name"].split()[:2]
        ).upper() or "?",
    }
    stats = build_stats(expenses, breakdown)
    transactions = build_transactions(recent)
    categories = build_categories(breakdown)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        filter=flt,
        presets=preset_keys,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
