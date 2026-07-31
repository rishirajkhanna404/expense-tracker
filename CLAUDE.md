# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendwise — a Flask-based personal expense tracker. Currency copy uses ₹ (INR). The codebase is a **learning scaffold**: `app.py` contains finished routes plus placeholder routes labeled "coming in Step N", and `database/db.py` is a header comment instructing implementers to provide `get_db()`, `init_db()`, and `seed_db()`. Auth (`/login`, `/register`), profile, and expense CRUD are not yet wired to the database — current handlers only `render_template`. The landing page, terms, and privacy pages are complete and shipped.

## Run / Develop

Virtualenv is already provisioned at `venv/`.

```bash
# Activate venv (macOS/zsh)
source venv/bin/activate

# Install/refresh deps
pip install -r requirements.txt

# Run dev server (http://localhost:5001, not 5000)
python app.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_routes.py

# Run a single test by name
pytest -k test_login
```

There is no build step, linter, formatter, or pre-commit config wired up. No `Makefile`, `pyproject.toml`, or `setup.cfg`.

## Architecture

Single-module Flask app — no blueprints, no `config.py`, no `models.py`, no `forms.py`. Every route lives in `app.py`. Convention is to extend `app.py` for new routes; refactor to blueprints only when the file gets unwieldy.

**Route map** (see `app.py`):
- Live: `/`, `/register` (GET-only, no form handler), `/login` (GET-only, no form handler), `/terms`, `/privacy`.
- Placeholders returning `"… coming in Step N"` strings: `/logout` (Step 3), `/profile` (Step 4), `/expenses/add` (Step 7), `/expenses/<int:id>/edit` (Step 8), `/expenses/<int:id>/delete` (Step 9).

**Templates** (`templates/`): all extend `base.html`, which carries the navbar, footer, Google Fonts (`DM Serif Display`, `DM Sans`), and shared CSS/JS includes. Three block regions: `{% block content %}`, `{% block head %}`, `{% block scripts %}`. Templates render the same templates on POST as on GET right now — the auth pages include `{% if error %}` blocks but no backend populates `error` yet, so the routes will need to switch to handling `request.method == "POST"` and passing an `error` variable.

**Database layer** (`database/`): empty `__init__.py` plus `db.py`, which is currently a comment-only placeholder. The interface to implement is documented in the file: `get_db()` (return a SQLite connection with `row_factory` set and foreign keys enabled), `init_db()` (`CREATE TABLE IF NOT EXISTS` for all tables), `seed_db()` (insert sample dev data). The SQLite file lives at the repo root as `expense_tracker.db` (gitignored).

**Static assets** (`static/`): one hand-written `css/style.css`, `js/main.js` (also a placeholder comment), and `js/landing.js` (the working YouTube "See how it works" modal — keep this dependency-free, no IFrame API). Modal pattern: iframe is rendered with `src="about:blank"` and a `data-src` attribute; the JS swaps `src` to `data-src` on open and back to `about:blank` on close to stop the video.

## Conventions to watch

- **Port 5001, not 5000.** `app.run(debug=True, port=5001)` in `app.py`.
- **Brand naming is inconsistent in the codebase.** "Spendwise" appears in `base.html` chrome (navbar brand, footer brand). "Spendwise" appears in marketing copy: the landing hero subtitle ("Spendwise helps you log expenses…"), the CTA section copy, and the modal title "See how Spendwise works". A commit message references "name-changes" — this rename is mid-flight. Confirm with the user which name to use before editing marketing copy.
- **Two hardcoded links in the footer** (`base.html:37-38`) point to `/terms` and `/privacy` as strings rather than `url_for("terms")` / `url_for("privacy")`. Prefer `url_for` for new links; leave existing ones unless the task touches them.
- **No CSRF protection, no auth middleware, no session handling yet.** When adding `POST` handlers, also introduce sessions/flashing before exposing login or register to real users.
- **Modal lazy-load iframe pattern** in `landing.js` is intentional (no YouTube IFrame API dependency). Don't pull it out unless asked.
- **Gitignored**: `venv/`, `expense_tracker.db`, `__pycache__/`, `*.pyc`, `*.pyo`, `.env`, `.DS_Store`, `.claude/plans/`.
