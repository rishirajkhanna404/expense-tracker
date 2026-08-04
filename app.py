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
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # If already signed in, the auth pages have nothing to offer.
    if session.get("user_id"):
        return redirect(url_for("landing"))

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
        return redirect(url_for("landing"))

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
        flash(f"Welcome back, {user['name']}.", "success")
        return redirect(url_for("landing"))

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
    return "Profile page — coming in Step 4"


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
