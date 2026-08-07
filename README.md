# Spendwise 💸

A personal expense tracker built with Flask and SQLite. Log expenses, see them broken down by category, and filter your history by date.

**🌐 Live demo:** [spendwise-web-production-b6cc.up.railway.app](https://spendwise-web-production-b6cc.up.railway.app/)

> **Demo account** — email `demo@spendwise.com`, password `demo123`
>
> ⚠️ **Heads up:** The live demo runs on Railway's ephemeral filesystem, so the database is wiped on every redeploy and idle-restart. Any accounts or expenses you create there will not survive — use the local setup below for real data.

---

## Features

- 🔐 **Authentication** — register, sign in, sign out, session-based
- 👤 **Profile dashboard** — total spent, transaction count, top category at a glance
- ➕ **Add expenses** — amount, category, date, optional description
- ✏️ **Edit expenses** — fix mistakes without leaving the profile page
- 📅 **Date filtering** — preset ranges (last 7 days / 30 days / month / year / all time) or custom start/end
- �️ **Category breakdown** — share-of-spend per category, sorted largest first
- � **Responsive UI** — DM Serif Display + DM Sans from Google Fonts

## Tech stack

| Layer | Choice |
|---|---|
| Web framework | Flask 3.1 |
| Database | SQLite (stdlib `sqlite3`) |
| Password hashing | `werkzeug.security` |
| Templates | Jinja2 |
| CSS / JS | Hand-written, no build step |
| Tests | pytest + pytest-flask |

## Project structure

```
expense-tracker/
├── app.py                  # All routes live here (single-module Flask)
├── database/
│   └── db.py               # SQLite connection, schema, CRUD helpers
├── templates/              # Jinja2 templates (extend base.html)
│   ├── base.html           # Navbar, footer, font + asset includes
│   ├── landing.html
│   ├── register.html
│   ├── login.html
│   ├── profile.html        # Dashboard: stats + transactions + categories
│   ├── add_expense.html
│   ├── edit_expense.html
│   ├── analytics.html
│   ├── terms.html
│   └── privacy.html
├── static/
│   ├── css/style.css
│   └── js/                 # main.js (placeholder) + landing.js (YouTube modal)
├── tests/
│   ├── conftest.py
│   └── test_06-date-filter-for-profile-page.py
├── requirements.txt
└── spendwise.db            # Local SQLite file (gitignored)
```

## Getting started

### Prerequisites

- Python 3.10+
- `venv` (already provisioned if you cloned the repo)

### Install & run

```bash
# Activate the virtualenv (macOS / zsh)
source venv/bin/activate

# Install / refresh dependencies
pip install -r requirements.txt

# Start the dev server → http://localhost:5001
python app.py
```

On first boot the app creates `spendwise.db` in the project root and seeds it with a demo account and 8 sample expenses covering every category.

### Run the tests

```bash
pytest                          # all tests
pytest tests/test_06-date-filter-for-profile-page.py
pytest -k test_login            # single test by name
```

## How it's organised

- **`app.py` is the whole app** — every route lives in one file. The project deliberately avoids blueprints, `config.py`, `models.py`, and `forms.py` to keep the scaffold approachable. Refactor to blueprints if the file gets unwieldy.
- **Templates extend `base.html`**, which carries the navbar, footer, and shared CSS/JS. Three block regions: `content`, `head`, `scripts`.
- **The database layer** is `database/db.py` — connection helper (`get_db`), schema (`init_db`), seed data (`seed_db`), and one function per query. Foreign keys are enabled per-connection.
- **Currency copy uses ₹ (INR)** throughout — `format_inr()` in `app.py` is the single source of truth.

## Allowed expense categories

`Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other`

Defined inline as `ALLOWED_CATEGORIES` in `app.py`. The form `<select>` is populated by sorting this set.

## Conventions

- **Port 5001**, not 5000 — `app.py` binds to `0.0.0.0:5001` locally, or `$PORT` on Railway.
- **Brand naming is mid-rename** — "Spendwise" in navbar/footer, "Spendwise" in marketing copy on the landing page. Confirm before editing marketing strings.
- **No CSRF, no auth middleware yet** — POST handlers should introduce sessions and flashing before the login/register flow is exposed to real users (sessions + `flash()` are already wired).
- **Footer terms/privacy links** are hardcoded as strings rather than `url_for()` calls — leave as-is unless the task touches them.

## Deployment

The app is currently deployed on Railway from the `main` branch — pushes to `main` trigger an automatic redeploy.

The repo was set up with the production startup block in `app.py`:

```python
if __name__ == "__main__":
    init_db()
    seed_db()
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
```

`init_db()` uses `CREATE TABLE IF NOT EXISTS`, and `seed_db()` is idempotent (it short-circuits if the demo email already exists), so it's safe to run on every boot.

## License

Personal learning project — no license specified.
