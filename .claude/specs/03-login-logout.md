# Spec: Login and Logout

## Overview
Wire the `/login` and `/logout` routes so a returning user can authenticate and sign out. After Step 02 created accounts but left login as a GET-only stub (POST returns 405), this step finishes the auth loop: `/login` accepts credentials, verifies the password hash against the `users` row written by `create_user()`, and on success establishes a session that subsequent steps (profile, expenses) can rely on. `/logout` clears that session and returns the user to the landing page so they can sign in as someone else or stop using the app.

## Depends on
- Step 01 — Database setup (`users` table with `id`, `name`, `email`, `password_hash`).
- Step 02 — User Registration (`create_user()` helper in `database/db.py` writes the hashed passwords we now verify against).

## Routes
- `POST /login` — verify email + password, establish a logged-in session, redirect to `/` — public (replaces the current GET-only stub; GET is also kept to render the form).
- `GET /login` — render the login form — public (existing route, accepts GET; the existing form posts to `/login`).
- `GET /logout` — clear the user session and redirect to `/` — public (replaces the current placeholder string response with a real handler that accepts GET or POST).

## Database changes
No database changes. We rely on the existing `users` columns (`id`, `name`, `email`, `password_hash`) created in Steps 01 and 02.

A new DB helper must be added to `database/db.py`:
- `get_user_by_email(email)` — returns the matching `users` row (as a `sqlite3.Row` dict-like object) or `None` if no user exists. Uses parameterised `SELECT ... WHERE email = ?`. Reuses `get_db()`.

## Templates
- **Create:** `templates/_macros.html` *(optional)* — a small Jinja macro for rendering flashed messages with the right CSS class. Only created if `register.html` and `login.html` would otherwise carry duplicated flash markup; otherwise the same `get_flashed_messages` block is inlined into `login.html` exactly as it lives in `register.html`.
- **Modify:** `templates/login.html`
  - Add a flash-messages block at the top of `auth-card` so the redirected "Account created — please sign in." message from Step 02 is visible on login.
  - Pre-fill the email input from `form.email` so users don't retype after a failed login.
  - Change the form `action` to `url_for('login')`.
  - Keep all existing visual design, all classes, and the `{% extends "base.html" %}` line.
- **Modify:** `templates/base.html`
  - Replace the hardcoded "Sign in" / "Get started" links in the navbar with a small conditional: if `session.user_id` is set, show the user's name (or email) and a "Log out" link to `url_for("logout")`; otherwise show the existing "Sign in" / "Get started" links. This is the first place the navbar reads session state — it gives logout a real entry point without adding a new page.
  - Do not introduce hex values — use existing CSS variables for any color changes.

## Files to change
- `app.py`
  - Add `from flask import session` to the existing Flask import.
  - Add `from database.db import get_user_by_email`.
  - Import `from werkzeug.security import check_password_hash`.
  - Update the existing `login()` route to accept `GET` and `POST`. On POST, look up the user by email, verify the password with `check_password_hash`, set `session["user_id"]` + `session["user_name"]` + `session["user_email"]` on success, or flash an error and re-render on failure.
  - Replace the placeholder `logout()` route so it does `session.clear()` and `redirect(url_for("landing"))`. Accept GET (the placeholder currently only handles GET — that's fine; logout links will use a plain link, not a form, to keep the implementation simple).
  - Add a small `@app.before_request` (or a `current_user` helper + filter / context processor) is **out of scope** for this step; we use `session.get("user_id")` checks directly in templates and routes for now.
- `database/db.py` — add `get_user_by_email(email)` next to `create_user`.
- `templates/login.html` — see "Templates" above.
- `templates/base.html` — see "Templates" above.
- `templates/register.html` — small consistency fix if needed so the navbar updates render correctly on `/register` too. No functional change; the existing flash messages keep working.

## Files to create
- None required. A `_macros.html` partial is optional and only created if duplicated flash markup is unavoidable. Default: inline the flash block directly into `login.html`, matching how `register.html` already does it.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` is already part of the installed `werkzeug` package (used today by `generate_password_hash` in `seed_db()` and `create_user()`).

## Rules for implementation
- No SQLAlchemy or any ORM. Use `sqlite3` directly via `get_db()`.
- Parameterised queries only — every `WHERE` / `INSERT` / `UPDATE` uses `?` placeholders.
- Verify passwords with `werkzeug.security.check_password_hash`. Never compare hashes with `==`; never store plaintext.
- `app.secret_key` is already set in `app.py` from Step 02 (required for both `flash()` and `session`).
- Server-side validation rules on `POST /login`:
  1. Both `email` and `password` fields are non-empty.
  2. Email is looked up case-insensitively (`.strip().lower()`, matching how Step 02 stored it).
  3. If no user is found, **or** `check_password_hash` returns `False`, the same generic "Invalid email or password" message is shown — never reveal which side was wrong.
  4. On success, set `session["user_id"]`, `session["user_name"]`, `session["user_email"]` and `redirect(url_for("landing"))`.
- Logout must be idempotent: if the session is already empty, `/logout` still redirects to `/` without raising.
- All templates extend `base.html`. New partials (if any) respect the same extension pattern.
- Use CSS variables for any color or spacing change — never hardcode hex.
- Use `url_for()` for every internal link — including the existing footer links to `/terms` and `/privacy` if they happen to be touched (default: don't touch them).
- Do not introduce CSRF protection in this step — the spec called this out as deferred until later steps. Keep a small note in code (`# Step 03: CSRF tokens not yet enabled`) only if it helps future readers; otherwise leave the comment out.

## Definition of done
- [ ] `GET /login` still renders the form (no regression).
- [ ] `POST /login` with the demo user's email (`demo@spendwise.com`) and password `demo123` sets a session and redirects to `/`.
- [ ] `POST /login` with the demo user's email and the **wrong** password flashes "Invalid email or password", does not set a session, and re-renders the form (200, not 302).
- [ ] `POST /login` with an email that is not in the `users` table flashes the same "Invalid email or password" message (no enumeration).
- [ ] `POST /login` with empty email or empty password re-renders the form with a validation error.
- [ ] After a successful login, the navbar on `/` (and every other page that extends `base.html`) shows the user's name and a "Log out" link instead of "Sign in" / "Get started".
- [ ] Visiting `/logout` clears the session and redirects to `/`. After logout, the navbar reverts to "Sign in" / "Get started".
- [ ] Visiting `/logout` when already logged out does not raise and still redirects to `/`.
- [ ] Passwords are never stored, logged, or compared in plaintext — verifiable by reading `app.py` and `database/db.py`.
- [ ] No unhandled exceptions appear in the server log during the happy path or the documented error paths.
- [ ] App still starts on port 5001 with `python app.py` after the changes.
- [ ] Manually following the full Step 02 → Step 03 flow end-to-end now works: register a new account on `/register`, follow the redirect to `/login`, sign in with those credentials, see the username in the navbar, click "Log out", and land back on `/` with the session cleared.
