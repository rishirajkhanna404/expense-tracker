"""Shared pytest fixtures for Spendwise tests.

These fixtures spin up the real Flask app (`app.py`) against a temporary
SQLite file so tests don't touch the project's `spendwise.db`. The temp
DB lives for the lifetime of the test session; per-test isolation is
provided by re-initialising the schema at the start of every test that
needs it.
"""

import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Session-scope temp DB path: set BEFORE `app` is imported so get_db() never
# opens the real spendwise.db. Using tempfile.NamedTemporaryFile gives us a
# real file on disk (sqlite3 needs an actual file for repeated connections),
# with `delete=False` so the path survives after we close our handle.
# ---------------------------------------------------------------------------

_TEMP_DB_FD, _TEMP_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="spendwise_test_")
os.close(_TEMP_DB_FD)

# Monkeypatch `database.db.DB_PATH` BEFORE the app is imported anywhere.
# This module is imported by pytest very early, so this assignment is in
# place before the first test pulls in `app.py`.
from database import db as db_mod  # noqa: E402  (deliberately after the patch)
db_mod.DB_PATH = _TEMP_DB_PATH
db_mod.init_db()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(monkeypatch):
    """Return the real Spendwise Flask app, configured for testing."""
    # Re-affirm the DB_PATH override per-test in case anything mutated it.
    from database import db as db_mod_local
    monkeypatch.setattr(db_mod_local, "DB_PATH", _TEMP_DB_PATH, raising=True)

    # Ensure tables exist (idempotent).
    db_mod_local.init_db()

    # Wipe rows from any prior test so the new test gets a clean slate.
    _wipe_db(db_mod_local)

    from app import app as flask_app

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-do-not-use-in-prod",
        WTF_CSRF_ENABLED=False,
    )
    yield flask_app

    # Post-test wipe — keeps the temp DB tidy and helps surface
    # accidental cross-test dependencies during local debugging.
    _wipe_db(db_mod_local)


def _wipe_db(db_mod_local):
    """Delete all rows from the test DB (safe to call on empty tables)."""
    conn = db_mod_local.get_db()
    conn.executescript(
        "DELETE FROM expenses; DELETE FROM users; DELETE FROM sqlite_sequence;"
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client(app):
    """An unauthenticated Flask test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """A Flask test client that is already logged in as the seed user.

    Mirrors `seed_db()` in `database/db.py` — inserts the demo user with
    email `demo@spendwise.com` and password `demo123`, plus the 8 sample
    expenses — then signs in via the public `/login` POST endpoint.
    """
    # Import lazily so any test fixture that monkeypatches DB_PATH runs
    # before the helper imports get cached.
    from database import db as db_mod_local
    db_mod_local.seed_db()

    client = app.test_client()
    resp = client.post(
        "/login",
        data={"email": db_mod_local.DEMO_EMAIL, "password": "demo123"},
        follow_redirects=False,
    )
    # Successful login returns a 302 redirect to /profile.
    assert resp.status_code == 302, (
        f"Login should redirect (302); got {resp.status_code}. "
        f"Body snippet: {resp.data[:200]!r}"
    )
    return client
