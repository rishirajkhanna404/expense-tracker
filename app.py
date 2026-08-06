import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_user_by_email, init_db, seed_db

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


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded sample data — Step 05 will replace these with DB queries.
    user = {
        "name": "Demo User",
        "email": "demo@spendwise.com",
        "member_since": "August 2026",
        "initials": "DU",
    }
    stats = {
        "total_spent": 2625.00,
        "total_spent_label": "₹2,625.00",
        "transaction_count": 8,
        "top_category": "Food",
    }
    transactions = [
        {"date": "12 Apr 2025", "description": "Groceries — weekly run", "category": "Food",          "amount": 250.00,  "amount_label": "₹250.00"},
        {"date": "11 Apr 2025", "description": "Metro card top-up",      "category": "Transport",     "amount": 60.00,   "amount_label": "₹60.00"},
        {"date": "10 Apr 2025", "description": "Electricity bill",       "category": "Bills",         "amount": 1200.00, "amount_label": "₹1,200.00"},
        {"date": "09 Apr 2025", "description": "New running shoes",      "category": "Shopping",      "amount": 450.00,  "amount_label": "₹450.00"},
        {"date": "08 Apr 2025", "description": "Movie tickets",          "category": "Entertainment", "amount": 180.00,  "amount_label": "₹180.00"},
        {"date": "05 Apr 2025", "description": "Dinner with friends",    "category": "Food",          "amount": 320.00,  "amount_label": "₹320.00"},
        {"date": "02 Apr 2025", "description": "Pharmacy",               "category": "Health",        "amount": 90.00,   "amount_label": "₹90.00"},
        {"date": "28 Mar 2025", "description": "Miscellaneous",          "category": "Other",         "amount": 75.00,   "amount_label": "₹75.00"},
    ]
    categories = [
        {"name": "Food",          "total": 570.00,  "total_label": "₹570.00",  "share": 22},
        {"name": "Bills",         "total": 1200.00, "total_label": "₹1,200.00","share": 46},
        {"name": "Shopping",      "total": 450.00,  "total_label": "₹450.00",  "share": 17},
        {"name": "Entertainment", "total": 180.00,  "total_label": "₹180.00",  "share": 7},
        {"name": "Health",        "total": 90.00,   "total_label": "₹90.00",   "share": 3},
        {"name": "Transport",     "total": 60.00,   "total_label": "₹60.00",   "share": 2},
        {"name": "Other",         "total": 75.00,   "total_label": "₹75.00",   "share": 3},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
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
