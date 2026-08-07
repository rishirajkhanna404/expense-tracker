# Spec: Add Expense

## Overview
Step 7 replaces the placeholder `/expenses/add` route with a real add-expense flow. Logged-in users can record a new expense by submitting an amount, category, date, and optional description. On success the user is redirected back to `/profile` so the new row is immediately visible in the transaction list, summary stats, and category breakdown. This is the first expense-mutation route — once it ships, `/profile` is no longer read-only and the demo data set in `seed_db()` becomes a starting point the user can grow. Edit (Step 8) and Delete (Step 9) build on the same pattern, so the conventions nailed down here carry forward.

## Depends on
- Step 1: Database setup (`expenses` table with `user_id`, `amount`, `category`, `date`, `description` exists)
- Step 2: User Registration (users exist so `user_id` foreign keys are valid)
- Step 3: Login / Logout (`session["user_id"]` is set for the logged-in user)
- Step 5: Backend routes for profile (`get_expenses_for_user` and helpers are wired up so the redirect-back target actually renders the new row)
- Step 6: Date filter for profile page (the form should respect the active date filter when redirecting, so the user sees a consistent view)

## Routes
- `GET /expenses/add` — render the add-expense form, pre-filled with sensible defaults (today's date for `date`, empty `amount`, empty `description`, no `category` selected). Access level: **logged-in**. Unauthenticated requests redirect to `/login` with a flash message.
- `POST /expenses/add` — validate the submitted form, insert the row, redirect to `/profile` (preserving any active date filter from the referrer if possible). Access level: **logged-in**. Unauthenticated requests redirect to `/login`.

No new routes beyond replacing the existing placeholder.

## Database changes
No schema changes. The `expenses` table already has every column this feature needs (`user_id`, `amount`, `category`, `date`, `description`, `created_at`).

A new DB helper must be added to `database/db.py`:
- `create_expense(user_id, amount, category, date, description=None)` — insert one row into `expenses`. Returns the new row's `id`. Uses parameterised `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`. Reuses `get_db()`. `description` may be `None` or empty string (stored as `NULL` if empty).

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`.
  - Uses the same auth-card / form layout as `login.html` and `register.html` for visual consistency.
  - Form fields:
    - `amount` — `<input type="number" name="amount" step="0.01" min="0.01" required>` with a `₹` prefix label.
    - `category` — `<select name="category" required>` with the seven fixed categories from spec 01 (Food, Transport, Bills, Health, Entertainment, Shopping, Other) as `<option>`s. First option is a disabled placeholder ("Select a category").
    - `date` — `<input type="date" name="date" required>`. Default value is today's date (ISO `YYYY-MM-DD`).
    - `description` — `<input type="text" name="description" maxlength="200">`. Optional, no `required` attribute. Placeholder text "What was this for?".
  - Submit button label: "Save expense".
  - Form `action` is `url_for("add_expense")`, method `POST`.
  - Top of the card: a flash-messages block (same shape as `register.html` / `login.html`) so validation errors from POST render in context.
  - Below the card: a small "Cancel" link back to `url_for("profile")`.
  - Pre-fills the form with the previously-submitted values on validation failure (so the user only has to fix what was wrong). Pass a `form` dict with the same keys as the field names.
- **Modify:** `templates/profile.html`
  - Add an "Add expense" entry-point — a button or link somewhere on the page (e.g. in the transaction list section header, or above the filter bar) that links to `url_for("add_expense")`. Without this entry point, the only way to reach the new route is by typing the URL, which is a bad UX.
- **Modify:** `templates/base.html`
  - No structural changes required. The navbar already reflects logged-in state from Step 03.

## Files to change
- `app.py`
  - Replace the placeholder `add_expense()` route with a real `GET` / `POST` handler. Add `from database.db import create_expense` to the existing import.
  - The route must:
    1. Require a logged-in user — if `session.get("user_id")` is missing, `flash("Please sign in to add an expense.", "error")` and `redirect(url_for("login"))`.
    2. On `GET`, render `add_expense.html` with `form={"amount": "", "category": "", "date": today_iso, "description": ""}`.
    3. On `POST`, pull `amount`, `category`, `date`, `description` from `request.form`, validate, then either re-render with errors or call `create_expense()` and redirect.
- `database/db.py` — add `create_expense(user_id, amount, category, date, description=None)` next to the existing query helpers.
- `templates/profile.html` — add the "Add expense" entry-point link/button.
- `templates/add_expense.html` — created (see Templates above).
- `static/css/style.css` — only if the form needs styling that the existing `auth-card` / form classes don't already cover. Default: reuse existing classes; no CSS changes unless something visibly breaks.

## Files to create
- `templates/add_expense.html` — see Templates above.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or any ORM. Use `sqlite3` directly via `get_db()`.
- Parameterised queries only — every `INSERT` / `SELECT` uses `?` placeholders. Never string-format values into SQL.
- All templates extend `base.html`.
- Use CSS variables for any color or spacing change — never hardcode hex values.
- No inline styles.
- Currency must always display as ₹ — never £ or $.
- Server-side validation rules on `POST /expenses/add`:
  1. All of `amount`, `category`, `date` are required; `description` is optional.
  2. `amount` must parse as a positive number greater than zero. Reject zero, negative, or non-numeric values with a clear message. Accept up to two decimal places (the `step="0.01"` on the input is a hint, not a server guarantee — re-validate on the server).
  3. `category` must be one of the seven fixed categories (Food, Transport, Bills, Health, Entertainment, Shopping, Other). Anything else is rejected — we don't let users invent categories.
  4. `date` must parse as a valid ISO `YYYY-MM-DD` string. Reject anything else (e.g. `"not-a-date"`).
  5. `description`, if provided, is trimmed; an empty string is stored as `NULL` (not `""`) so the existing `description or ""` rendering in `build_transactions()` works unchanged.
  6. On validation failure, re-render `add_expense.html` (HTTP 200) with a flash error and the user's submitted values preserved in the `form` dict. Do **not** redirect.
- On successful insert, `flash("Expense added.", "success")` and redirect to `url_for("profile")`. The redirect should preserve any active date filter if the user came from a filtered profile view — simplest approach: read the `Referer` header and, if it points at `/profile` with a query string, redirect there instead of bare `/profile`. If the referrer is missing or points elsewhere, fall back to plain `/profile`.
- The new row's `created_at` is set by the database default `datetime('now')` — no need to pass it.
- `description` length is capped at 200 characters in the template; on the server, truncate silently or reject with a clear error. Truncate is simpler.
- The `amount` field on the wire is a string. Convert to `float()` for the DB insert. Reject non-numeric input without raising — wrap in a `try / except ValueError`.
- Follow the same auth-gate pattern as `/analytics` (see `app.py:279-285`) — `session.get("user_id")` check at the top of the handler, redirect to login with a flash on miss.
- `url_for()` for every internal link — the new "Add expense" entry point, the "Cancel" link, the form `action`.

## Definition of done
- [ ] `GET /expenses/add` while logged in renders the form with today's date pre-filled and no category selected.
- [ ] `GET /expenses/add` while logged out redirects to `/login` with a flash message (302).
- [ ] `POST /expenses/add` with `amount=150`, `category="Food"`, `date="2026-08-07"`, `description="Lunch"` inserts a row and redirects to `/profile` (302).
- [ ] After the redirect, the new row is visible in the transaction table on `/profile` (newest-first ordering) and the total / count / category breakdown have updated.
- [ ] `POST /expenses/add` with `amount=0` re-renders the form (200) with a validation error and the submitted values preserved — no row is inserted.
- [ ] `POST /expenses/add` with `amount=-50` is rejected with the same error.
- [ ] `POST /expenses/add` with `amount="abc"` is rejected without a 500 (the server catches `ValueError`).
- [ ] `POST /expenses/add` with `category="Groceries"` (not in the allowed list) is rejected.
- [ ] `POST /expenses/add` with `date="2026/08/07"` (wrong format) is rejected.
- [ ] `POST /expenses/add` with `description=""` inserts the row with `description = NULL` (not `""`).
- [ ] `POST /expenses/add` with `description="   "` (whitespace only) is normalised to `NULL`.
- [ ] The profile page exposes an "Add expense" link / button that navigates to `GET /expenses/add`.
- [ ] All amounts on the new flow display the ₹ symbol where applicable.
- [ ] No unhandled exceptions appear in the server log during the happy path or any of the documented error paths.
- [ ] App still starts on port 5001 with `python app.py` after the changes.
