# Spec: Date Filter For Profile Page

## Overview
Step 6 adds date-range filtering to the profile page so users can scope their
expense history to a specific window — for example, "this month", "last 30
days", or a custom start/end date pair. The filter lives on the `/profile`
route and affects the four data sections currently rendered there: the
transaction list, the summary stats (total spent, transaction count, top
category), and the category breakdown. The user info card is unaffected.
Out of scope for this step: filtering on category, amount range, or free-text
description search — those can be later steps.

## Depends on
- Step 1: Database setup (tables and `get_db()` exist)
- Step 2: Registration (users are stored in the database)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page static UI (template already renders all four sections)
- Step 5: Backend routes for profile page (`get_expenses_for_user`,
  `get_category_breakdown_for_user`, `build_stats`, `build_transactions`,
  `build_categories` are wired up)

## Routes
- `GET /profile` — extended to accept `start`, `end`, and `range` query
  parameters and apply the resulting date filter to the four dynamic sections.
  Access level: **logged-in**.

  Query parameters (all optional; missing or invalid → treat as "all time"):
  - `range` — preset shortcut. One of `this-month`, `last-month`, `last-30`,
    `last-90`, `ytd`. When supplied, the route derives `start` and `end` from
    it; explicit `start` / `end` still take precedence.
  - `start` — ISO date string `YYYY-MM-DD`. Inclusive lower bound on
    `expenses.date`.
  - `end` — ISO date string `YYYY-MM-DD`. Inclusive upper bound on
    `expenses.date`.

  Response is the same `profile.html` template with extra context: the
  currently-applied `filter` dict and the list of available `presets`.

No new routes.

## Database changes
No database changes. The existing `expenses.date` column (stored as ISO
`YYYY-MM-DD` text) is sufficient — filtering is a `WHERE date BETWEEN ? AND ?`
clause on top of the existing query helpers.

## Templates
- **Modify**: `templates/profile.html`
  - Add a filter bar above the stats row with a "range" preset `<select>`
    (or equivalent controls) and "From" / "To" `<input type="date">` fields
    wired to a `<form method="get" action="{{ url_for('profile') }}">`.
  - The form's submit button is labelled "Apply".
  - A "Clear" link/button (`/profile` with no query string) resets the
    filter to "all time".
  - When a filter is active and the result set is empty, the transaction
    table and category breakdown should render a friendly empty state
    (e.g. "No transactions in this date range.") instead of vanishing.
  - The currently-active preset is marked `selected` in the dropdown so the
    user can see what they applied.

## Files to change
- `app.py` — extend `profile()` to parse `range` / `start` / `end` from
  `request.args`, build a `filter` dict, and pass the date bounds down to the
  query helpers and template
- `database/db.py` — add a `start_date` and `end_date` parameter to
  `get_expenses_for_user` and `get_category_breakdown_for_user` (both default
  to `None` so existing callers keep working)
- `templates/profile.html` — add the filter bar, the empty-state messaging,
  and the currently-active preset selection
- `static/css/style.css` — style the filter bar (form row, inputs, select,
  submit button) using existing CSS variables

## Files to create
- `database/filters.py` — small pure helper module (no Flask imports) that
  resolves a raw query-param dict into a clean `filter` payload:
  - `resolve_filter(args)` → dict with keys `start`, `end`, `preset`,
    `label` (human-readable summary like "This month" or "01 Aug 2026 —
    31 Aug 2026"), and `active` (bool).
  - `PRESETS` — a module-level dict of `preset_key → (start_date, end_date)`
    tuples, computed against today's date when the helper is called so the
    presets stay rolling.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- Invalid `start` / `end` strings (anything that doesn't parse as
  `YYYY-MM-DD`) are silently ignored — fall back to "all time" rather than
  400-ing
- `end` is inclusive — query uses `date BETWEEN ? AND ?` with the strings
  passed through unchanged (SQLite compares ISO date strings lexically,
  which works because the format is fixed-width)
- Empty result set must not crash the page — `build_transactions` and
  `build_categories` already handle `[]`; the template just needs the
  empty-state copy
- The filter form must work without JavaScript — a plain GET form with a
  submit button is enough. JS is optional polish, not a hard requirement
- The currently-active preset takes precedence in `resolve_filter` so the
  dropdown reflects what the user actually applied (e.g. if the URL is
  `?range=last-30`, that is shown as selected, not "Custom")
- Date math uses the `datetime` module — no `dateutil`, no `pandas`
- The "Clear" link is a plain `/profile` link, not a form button — the URL
  is the state, and stripping query params resets state

## Tests to write

### Unit tests
File: `tests/test_date_filter.py`

| Function | Input | Expected output |
|---|---|---|
| `resolve_filter` | `{}` (no args) | `{"start": None, "end": None, "preset": None, "label": "All time", "active": False}` |
| `resolve_filter` | `{"range": "this-month"}` | `start`/`end` both set within the current month, `preset == "this-month"`, `label == "This month"`, `active == True` |
| `resolve_filter` | `{"range": "last-30"}` | exactly 30-day window ending today |
| `resolve_filter` | `{"start": "2026-08-01", "end": "2026-08-31"}` | `start`/`end` echoed back, `preset == None`, `label` describes the range, `active == True` |
| `resolve_filter` | `{"start": "not-a-date"}` | falls back to no filter (`active == False`) |
| `get_expenses_for_user` with `start`/`end` | user with expenses in range + outside | only in-range rows returned, ordered newest first |
| `get_expenses_for_user` with `start` only | expenses before and after start | only expenses with `date >= start` |
| `get_expenses_for_user` with `end` only | expenses before and after end | only expenses with `date <= end` |
| `get_category_breakdown_for_user` with `start`/`end` | user with expenses in range + outside | categories only reflect in-range expenses; `total` is the in-range sum |

### Route tests
File: `tests/test_profile_filter_route.py`

`GET /profile?range=this-month` — authenticated as seed user:
- Returns 200
- Only expenses in the current month appear in the transaction table
- `total_spent` matches the in-range sum, not the lifetime total
- `transaction_count` matches the in-range count
- Category breakdown sums to the in-range total
- Response contains the filter bar markup

`GET /profile?start=2026-08-10&end=2026-08-20` — authenticated:
- Returns 200
- Only expenses with `date` in `[2026-08-10, 2026-08-20]` are visible
- `total_spent` reflects the filtered set

`GET /profile?range=invalid` — authenticated:
- Returns 200 (does not error)
- Behaves like "all time" (no filtering applied)

`GET /profile?start=garbage` — authenticated:
- Returns 200
- Behaves like "all time"

`GET /profile` (no query) — authenticated:
- Returns 200
- All expenses are visible (regression check that the default path still
  works)
- Filter bar shows "All time" as the selected option

`GET /profile?range=this-month` — unauthenticated:
- Redirects to `/login` (302)

## Definition of done
- [ ] Visiting `/profile?range=this-month` as the seed user shows only the
      seed expenses that fall in the current month
- [ ] Visiting `/profile?start=2026-08-10&end=2026-08-20` shows only expenses
      between those two dates
- [ ] Visiting `/profile` with no query string still shows all 8 seed
      expenses (no regression)
- [ ] The total spent, transaction count, and category breakdown all reflect
      the filtered set — not the lifetime totals
- [ ] An invalid `range` value (e.g. `?range=garbage`) does not 500 — the
      page renders the unfiltered view
- [ ] A "Clear" control is present in the filter bar and resets the URL to
      `/profile` with no query string
- [ ] When the filter returns no expenses, the transaction table and
      category breakdown show an empty-state message instead of disappearing
- [ ] The filter form works without JavaScript enabled (plain GET submit)
- [ ] Unauthenticated requests to `GET /profile?range=this-month` still
      redirect to `/login`
- [ ] All amounts continue to display the ₹ symbol
