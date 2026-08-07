import sqlite3
from werkzeug.security import generate_password_hash


# Project-root SQLite file. Created on first run, gitignored.
DB_PATH = "spendwise.db"

# Demo account for development. Password is "demo123" (hashed below).
DEMO_EMAIL = "demo@spendwise.com"

# (amount, category, date, description) — one row per category, plus a second
# Food row so all 7 spec categories are covered with 8 total expenses.
SAMPLE_EXPENSES = [
    (250.00,  "Food",          "2026-08-01", "Groceries — weekly run"),
    (60.00,   "Transport",     "2026-08-02", "Metro card top-up"),
    (1200.00, "Bills",         "2026-08-03", "Electricity bill"),
    (450.00,  "Shopping",      "2026-08-05", "New running shoes"),
    (180.00,  "Entertainment", "2026-08-08", "Movie tickets"),
    (320.00,  "Food",          "2026-08-12", "Dinner with friends"),
    (90.00,   "Health",        "2026-08-15", "Pharmacy"),
    (75.00,   "Other",         "2026-08-20", "Miscellaneous"),
]


def get_db():
    """Open a SQLite connection with dict-like rows and FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # PRAGMA foreign_keys is per-connection in SQLite — must be set every time.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they don't exist yet."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def seed_db():
    """Insert the demo user + 8 sample expenses. Safe to call repeatedly."""
    conn = get_db()
    cur = conn.cursor()

    # Idempotency guard: skip entirely if the demo account already exists.
    cur.execute("SELECT 1 FROM users WHERE email = ?", (DEMO_EMAIL,))
    if cur.fetchone() is not None:
        conn.close()
        return

    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", DEMO_EMAIL, generate_password_hash("demo123")),
    )
    user_id = cur.lastrowid

    for amount, category, date, description in SAMPLE_EXPENSES:
        cur.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )

    conn.commit()
    conn.close()


def create_user(name, email, password):
    """Insert a new user with a hashed password. Returns the new user id.

    Raises sqlite3.IntegrityError if the email is already taken (UNIQUE constraint).
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def create_expense(user_id, amount, category, date, description=None):
    """Insert a new expense row. Returns the new row's id.

    `description` is stored as NULL when empty/None so the existing
    `description or ""` rendering in build_transactions() keeps working.
    Raises sqlite3.IntegrityError if `user_id` doesn't exist (FK violation).
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the user row matching `email`, or None.

    Caller is expected to have normalised the email (strip + lower) so that
    the comparison matches how create_user() stores it.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT id, name, email, password_hash, created_at "
            "FROM users WHERE email = ?",
            (email,),
        )
        return cur.fetchone()  # sqlite3.Row or None
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return the user row for `user_id`, or None.

    Selects only the columns the profile view needs (never password_hash).
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT id, name, email, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        return cur.fetchone()  # sqlite3.Row or None
    finally:
        conn.close()


def get_expenses_for_user(user_id, limit=None, start_date=None, end_date=None):
    """Return the user's expenses as a list of sqlite3.Row, newest first.

    Ordering is `date DESC, id DESC` so same-day rows are stable. When
    `limit` is given, appends `LIMIT ?`; otherwise returns the full
    history. When `start_date` / `end_date` (ISO YYYY-MM-DD strings) are
    supplied, the query is scoped with an inclusive `date >= ?` and /
    or `date <= ?` clause — both bounds may be passed independently.
    """
    conn = get_db()
    try:
        clauses = ["user_id = ?"]
        params = [user_id]
        if start_date is not None:
            clauses.append("date >= ?")
            params.append(start_date)
        if end_date is not None:
            clauses.append("date <= ?")
            params.append(end_date)
        where = " AND ".join(clauses)

        if limit is None:
            cur = conn.execute(
                f"SELECT id, amount, category, date, description "
                f"FROM expenses WHERE {where} "
                f"ORDER BY date DESC, id DESC",
                params,
            )
        else:
            cur = conn.execute(
                f"SELECT id, amount, category, date, description "
                f"FROM expenses WHERE {where} "
                f"ORDER BY date DESC, id DESC LIMIT ?",
                params + [limit],
            )
        return cur.fetchall()
    finally:
        conn.close()


def get_category_breakdown_for_user(user_id, start_date=None, end_date=None):
    """Return [(category, total), ...] grouped by category, largest first.

    Same date-scoping rules as `get_expenses_for_user`. Used by the
    profile category-breakdown section.
    """
    conn = get_db()
    try:
        clauses = ["user_id = ?"]
        params = [user_id]
        if start_date is not None:
            clauses.append("date >= ?")
            params.append(start_date)
        if end_date is not None:
            clauses.append("date <= ?")
            params.append(end_date)
        where = " AND ".join(clauses)

        cur = conn.execute(
            f"SELECT category, SUM(amount) AS total "
            f"FROM expenses WHERE {where} "
            f"GROUP BY category "
            f"ORDER BY total DESC",
            params,
        )
        return cur.fetchall()
    finally:
        conn.close()
