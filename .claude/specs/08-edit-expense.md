# Spec: Edit Expense

## Overview
Step 8 replaces the placeholder `/expenses/<int:id>/edit` route with a real edit-expense flow. Logged-in users can update an existing expense they own — change the amount, category, date, or description — by submitting a form pre-populated with the row's current values. On success the user is bounced back to `/profile` (preserving any active date filter) so the updated row is immediately visible in the transaction list, summary stats, and category breakdown. This is the second expense-mutation route; it reuses every convention nailed down in Step 7 (validation rules, ALLOWED_CATEGORIES, flash messages, referrer-aware redirect). Delete (Step 9) follows the same auth + ownership pattern.

## Depends on
- Step 1: Database setup (`expenses` table with all editable columns exists)
- Step 2: User Registration (users exist so `user_id` foreign keys are valid)
- Step 3: Login / Logout (`session["user_id"]` is set for the logged-in user)
- Step 5: Backend routes for profile (`get_expenses_for_user` and helpers are wired up so the redirect-back target re-renders the updated row)
- Step 6: Date filter for profile page (the redirect should preserve the active filter, same as Step 7)
- Step 7: Add Expense (validation rules, `ALLOWED_CATEGORIES`, flash message style, referrer-aware redirect — copy the pattern, don't reinvent it)

## Routes
- `GET /expenses/<int:id>/edit` — render the edit form pre-populated with the row's current values. Access level: **logged-in**. Unauthenticated requests redirect to `/login` with a flash message. Requests targeting an `id` that doesn't exist, or that belongs to a different user, return 404 (don't leak existence).
- `POST /expenses/<int:id>/edit` — validate the submitted form, update the row, redirect to `/profile` (preserving any active date filter from the referrer if possible). Access level: **logged-in**. Same ownership / 404 rules as `GET`.

No new routes beyond replacing the existing placeholder.

## Database changes
No schema changes. The `expenses` table already has every editable column (`amount`, `category`, `date`, `description`).

A new DB helper must be added to `database/db.py`:
- `get_expense_by_id(expense_id, user_id)` — return the expense row if it belongs to `user_id`, else `None`. Selects `id, user_id, amount, category, date, description`. Uses parameterised `SELECT … WHERE id = ? AND user_id = ?`. This combines fetch + ownership check in one round trip, so the route can 404 on miss without a separate auth check.
- `update_expense(expense_id, user_id, amount, category, date, description)` — update an expense row, scoped to the owning user. Returns the number of rows changed (0 if no row matched, which the route treats as a 404). Uses parameterised `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?`. `description` may be `None` (stored as `NULL`). Reuses `get_db()`.

## Templates
- **Create:** `templates/edit_expense.html`
  - Extends `base.html`.
  - Mirrors `add_expense.html` layout exactly — same `auth-section` / `auth-container` / `auth-card` / `form-group` classes, same flash-messages block at the top of the card, same `url_for('profile')` "Cancel" link at the bottom.
  - Form fields (identical to add, pre-populated from `form`):
    - `amount` — `<input type="number" name="amount" step="0.01" min="0.01" required>` with a `₹` prefix label.
    - `category` — `<select name="category" required>` with the seven fixed categories from spec 01 (Food, Transport, Bills, Health, Entertainment, Shopping, Other) as `<option>`s. First option is a disabled placeholder ("Select a category").
    - `date` — `<input type="date" name="date" required>`.
    - `description` — `<input type="text" name="description" maxlength="200">`. Optional, no `required` attribute. Placeholder text "What was this for?".
  - Submit button label: "Save changes".
  - Form `action` is `url_for("edit_expense", id=expense.id)`, method `POST`.
  - Pre-fills the form with the row's current values on `GET`, or with the user's submitted values on validation failure (so they only have to fix what was wrong). Pass a `form` dict with the same keys as the field names; on `GET`, default `description` to empty string when the row stores `NULL`.
- **Modify:** `templates/profile.html`
  - Add an "Edit" entry-point per transaction row — a small link or icon button in the row's actions cell that links to `url_for("edit_expense", id=row.id)`. Without this entry point, the only way to reach the new route is by typing the URL, which is a bad UX. (A future delete entry-point will live next to it.)
- **Modify:** `templates/base.html`
  - No structural changes required. The navbar already reflects logged-in state from Step 03.

## Files to change
- `app.py`
  - Replace the placeholder `edit_expense(id)` route with a real `GET` / `POST` handler. Add `from database.db import get_expense_by_id, update_expense` to the existing import.
  - The route must:
    1. Require a logged-in user — if `session.get("user_id")` is missing, `flash("Please sign in to edit an expense.", "error")` and `redirect(url_for("login"))`.
    2. Fetch the row via `get_expense_by_id(id, session["user_id"])`. If `None`, abort with `404` (don't leak whether the id exists or belongs to someone else).
    3. On `GET`, build `form = {"amount": str(row["amount"]), "category": row["category"], "date": row["date"], "description": row["description"] or ""}` and render `edit_expense.html` with the row + form + sorted `ALLOWED_CATEGORIES`.
    4. On `POST`, pull `amount`, `category`, `date`, `description` from `request.form`, validate using the same rules as Step 7 (see Rules), then either re-render with errors or call `update_expense()` and redirect. Use the row's id when re-rendering so the form `action` resolves correctly.
- `database/db.py` — add `get_expense_by_id(expense_id, user_id)` and `update_expense(expense_id, user_id, amount, category, date, description)` next to the existing query helpers.
- `templates/profile.html` — add the per-row "Edit" link.
- `templates/edit_expense.html` — created (see Templates above).
- `static/css/style.css` — only if the row actions cell needs styling that existing classes don't already cover. Default: reuse existing classes; no CSS changes unless something visibly breaks.

## Files to create
- `templates/edit_expense.html` — see Templates above.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or any ORM. Use `sqlite3` directly via `get_db()`.
- Parameterised queries only — every `SELECT` / `UPDATE` uses `?` placeholders. Never string-format values into SQL.
- All templates extend `base.html`.
- Use CSS variables for any color or spacing change — never hardcode hex values.
- No inline styles.
- Currency must always display as ₹ — never £ or $.
- Ownership check is part of every query (`WHERE id = ? AND user_id = ?`), not a separate Python check. This way users cannot mutate rows that aren't theirs even if a route handler has a bug.
- Missing rows (id doesn't exist, or belongs to another user) return `404` — never `403`, since `403` leaks that the row exists. Use `flask.abort(404)`.
- Server-side validation rules on `POST /expenses/<int:id>/edit` (identical to Step 7):
  1. All of `amount`, `category`, `date` are required; `description` is optional.
  2. `amount` must parse as a positive number greater than zero. Reject zero, negative, or non-numeric values with a clear message. Accept up to two decimal places (the `step="0.01"` on the input is a hint, not a server guarantee — re-validate on the server).
  3. `category` must be one of the seven fixed categories (Food, Transport, Bills, Health, Entertainment, Shopping, Other). Anything else is rejected — we don't let users invent categories.
  4. `date` must parse as a valid ISO `YYYY-MM-DD` string. Reject anything else (e.g. `"not-a-date"`).
  5. `description`, if provided, is trimmed; an empty string is stored as `NULL` (not `""`) so the existing `description or ""` rendering in `build_transactions()` works unchanged.
  6. On validation failure, re-render `edit_expense.html` (HTTP 200) with a flash error and the user's submitted values preserved in the `form` dict. Do **not** redirect.
- On successful update, `flash("Expense updated.", "success")` and redirect to `url_for("profile")`. The redirect should preserve any active date filter if the user came from a filtered profile view — same pattern as Step 7: read the `Referer` header and, if it points at `/profile` with a query string, redirect there instead of bare `/profile`. If the referrer is missing or points elsewhere, fall back to plain `/profile`.
- The row's `created_at` is not editable and must not be touched by the `UPDATE` statement.
- `description` length is capped at 200 characters in the template; on the server, truncate silently (same as Step 7).
- The `amount` field on the wire is a string. Convert to `float()` for the DB update. Reject non-numeric input without raising — wrap in a `try / except ValueError`.
- Follow the same auth-gate pattern as `/analytics` (see `app.py:279-285`) and `/expenses/add` (see `app.py:286-288`) — `session.get("user_id")` check at the top of the handler, redirect to login with a flash on miss.
- `url_for()` for every internal link — the per-row "Edit" link, the "Cancel" link, the form `action`.
- Reuse the `ALLOWED_CATEGORIES` constant from `app.py` — don't redefine the list inline.

## Definition of done
- [ ] `GET /expenses/<id>/edit` while logged in renders the form pre-populated with the row's current values, with the row's category selected in the dropdown.
- [ ] `GET /expenses/<id>/edit` while logged out redirects to `/login` with a flash message (302).
- [ ] `GET /expenses/<id>/edit` for an id that doesn't exist returns 404 (not 500, not 200).
- [ ] `GET /expenses/<id>/edit` for an id that belongs to a different user returns 404 (not 403 — must not leak existence).
- [ ] `POST /expenses/<id>/edit` with valid fields updates the row and redirects to `/profile` (302).
- [ ] After the redirect, the updated row is visible in the transaction table on `/profile` with the new values, and totals / count / category breakdown reflect the change.
- [ ] `POST /expenses/<id>/edit` with `amount=0` re-renders the form (200) with a validation error and the submitted values preserved — no row is updated.
- [ ] `POST /expenses/<id>/edit` with `amount=-50` is rejected with the same error.
- [ ] `POST /expenses/<id>/edit` with `amount="abc"` is rejected without a 500 (the server catches `ValueError`).
- [ ] `POST /expenses/<id>/edit` with `category="Groceries"` (not in the allowed list) is rejected.
- [ ] `POST /expenses/<id>/edit` with `date="2026/08/07"` (wrong format) is rejected.
- [ ] `POST /expenses/<id>/edit` with `description=""` stores `NULL` (not `""`) — confirmed by re-fetching the row.
- [ ] `POST /expenses/<id>/edit` with `description="   "` (whitespace only) is normalised to `NULL`.
- [ ] `POST /expenses/<other_user_id>/edit` returns 404 — user A cannot edit user B's expenses.
- [ ] The profile page exposes a per-row "Edit" link that navigates to `GET /expenses/<id>/edit`.
- [ ] All amounts on the new flow display the ₹ symbol where applicable.
- [ ] No unhandled exceptions appear in the server log during the happy path or any of the documented error paths.
- [ ] App still starts on port 5001 with `python app.py` after the changes.
