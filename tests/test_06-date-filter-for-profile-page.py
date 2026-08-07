"""Tests for Step 6 — date filter for the /profile page.

Spec: .claude/specs/06-date-filter-for-profile-page.md

These tests pin the behaviour described in the spec, NOT the implementation.
If the implementation has a bug, the test still asserts the contract.

Coverage map:

  Unit tests on `database.filters.resolve_filter`:
    - test_resolve_filter_no_args
    - test_resolve_filter_this_month
    - test_resolve_filter_last_30
    - test_resolve_filter_custom_range
    - test_resolve_filter_invalid_start
    - test_resolve_filter_invalid_range

  Unit tests on `database.db.get_expenses_for_user` with date bounds:
    - test_get_expenses_both_bounds
    - test_get_expenses_start_only
    - test_get_expenses_end_only
    - test_get_expenses_no_bounds_regression

  Unit tests on `database.db.get_category_breakdown_for_user` with date bounds:
    - test_get_category_breakdown_with_bounds
    - test_get_category_breakdown_no_bounds_regression

  Route tests on `GET /profile`:
    - test_profile_unauthenticated_redirects
    - test_profile_authenticated_this_month
    - test_profile_authenticated_custom_range
    - test_profile_authenticated_invalid_range_does_not_500
    - test_profile_authenticated_invalid_start_falls_back
    - test_profile_authenticated_no_query_shows_all
    - test_profile_authenticated_this_month_has_clear_link
    - test_profile_authenticated_empty_range_shows_empty_state
    - test_profile_amounts_display_rupee
"""

from datetime import date

import pytest

from database import db as db_mod
from database.filters import resolve_filter


# ===========================================================================
# Unit tests on `database.filters.resolve_filter`
# ===========================================================================

class TestResolveFilter:

    def test_resolve_filter_no_args(self):
        """Spec: empty query args → no filter applied, label 'All time'.

        Covers spec bullet: `resolve_filter({})` → start=None, end=None,
        preset=None, label="All time", active=False.
        """
        result = resolve_filter({})
        assert result["start"] is None
        assert result["end"] is None
        assert result["preset"] is None
        assert result["label"] == "All time"
        assert result["active"] is False

    def test_resolve_filter_this_month(self):
        """Spec: `range=this-month` → bounds set within the current month.

        With today frozen to 2026-08-07 (per spec test), the expected
        bounds are start=2026-08-01, end=2026-08-31.
        """
        frozen_today = date(2026, 8, 7)
        result = resolve_filter(
            {"range": "this-month"}, today=frozen_today
        )
        assert result["start"] == "2026-08-01"
        assert result["end"] == "2026-08-31"
        assert result["preset"] == "this-month"
        assert result["label"] == "This month"
        assert result["active"] is True

    def test_resolve_filter_last_30(self):
        """Spec: `range=last-30` → exactly 30-day window ending today."""
        frozen_today = date(2026, 8, 7)
        result = resolve_filter({"range": "last-30"}, today=frozen_today)
        assert result["active"] is True
        assert result["preset"] == "last-30"
        assert result["start"] == "2026-07-09"
        assert result["end"] == "2026-08-07"

    def test_resolve_filter_custom_range(self):
        """Spec: explicit start/end echoed back; preset is None."""
        result = resolve_filter({
            "start": "2026-08-01",
            "end": "2026-08-31",
        })
        assert result["start"] == "2026-08-01"
        assert result["end"] == "2026-08-31"
        assert result["preset"] is None
        assert result["active"] is True
        # Spec: label describes the range. Accept any human-readable
        # description that mentions both dates (or both ends of the
        # range) — the exact wording is implementation-defined.
        assert result["label"] != "All time"
        assert "2026" in result["label"] or "Aug" in result["label"]

    def test_resolve_filter_invalid_start(self):
        """Spec: invalid start silently falls back to no filter."""
        result = resolve_filter({"start": "not-a-date"})
        assert result["active"] is False
        assert result["start"] is None

    def test_resolve_filter_invalid_range(self):
        """Spec: an unknown preset key → preset=None, no filter applied."""
        result = resolve_filter({"range": "garbage"})
        assert result["preset"] is None
        assert result["active"] is False
        assert result["label"] == "All time"


# ===========================================================================
# Unit tests on `database.db.get_expenses_for_user` with date bounds
# ===========================================================================

# The seed dataset (mirrors `db.SAMPLE_EXPENSES`) — one row per category
# plus a second Food row, all in August 2026.
SEED_EXPENSES = db_mod.SAMPLE_EXPENSES
EXPECTED_TOTAL = sum(row[0] for row in SEED_EXPENSES)
EXPECTED_COUNT = len(SEED_EXPENSES)
assert EXPECTED_COUNT == 8, (
    "Spec assumes 8 seed expenses; check db.SAMPLE_EXPENSES."
)


def _get_demo_user_id():
    """Return the demo user's id (the seed inserts exactly one)."""
    row = db_mod.get_user_by_email(db_mod.DEMO_EMAIL)
    assert row is not None, "Demo user must exist for this test."
    return row["id"]


class TestGetExpensesWithBounds:

    def test_get_expenses_both_bounds(self, auth_client, app):
        """Only in-range rows returned, ordered newest first."""
        with app.app_context():
            user_id = _get_demo_user_id()
            rows = db_mod.get_expenses_for_user(
                user_id,
                start_date="2026-08-10",
                end_date="2026-08-20",
            )
        # Seed expenses in [2026-08-10, 2026-08-20]:
        #   2026-08-12 Food / 2026-08-15 Health / 2026-08-20 Other  → 3 rows
        assert len(rows) == 3, (
            f"Expected 3 in-range expenses, got {len(rows)}: "
            f"{[r['date'] for r in rows]}"
        )
        dates = [r["date"] for r in rows]
        assert dates == sorted(dates, reverse=True), (
            "Rows must be ordered newest first."
        )

    def test_get_expenses_start_only(self, auth_client, app):
        """Start bound only: includes every expense on or after start."""
        with app.app_context():
            user_id = _get_demo_user_id()
            rows = db_mod.get_expenses_for_user(
                user_id, start_date="2026-08-10"
            )
        # All expenses from 2026-08-10 onward in the seed:
        # 12, 15, 20 → 3 rows
        assert len(rows) == 3
        for row in rows:
            assert row["date"] >= "2026-08-10", (
                f"Row date {row['date']} must be >= start bound"
            )

    def test_get_expenses_end_only(self, auth_client, app):
        """End bound only: includes every expense on or before end."""
        with app.app_context():
            user_id = _get_demo_user_id()
            rows = db_mod.get_expenses_for_user(
                user_id, end_date="2026-08-05"
            )
        # Seed expenses on or before 2026-08-05:
        # 01, 02, 03, 05 → 4 rows
        assert len(rows) == 4, (
            f"Expected 4 expenses on or before 2026-08-05, got {len(rows)}"
        )
        for row in rows:
            assert row["date"] <= "2026-08-05", (
                f"Row date {row['date']} must be <= end bound"
            )

    def test_get_expenses_no_bounds_regression(self, auth_client, app):
        """No bounds: full history returned (8 rows)."""
        with app.app_context():
            user_id = _get_demo_user_id()
            rows = db_mod.get_expenses_for_user(user_id)
        assert len(rows) == EXPECTED_COUNT
        # Newest-first ordering across the full set:
        dates = [r["date"] for r in rows]
        assert dates == sorted(dates, reverse=True)


class TestGetCategoryBreakdownWithBounds:

    def test_get_category_breakdown_with_bounds(self, auth_client, app):
        """Total reflects only in-range expenses; categories with no
        in-range rows are omitted.
        """
        with app.app_context():
            user_id = _get_demo_user_id()
            # Window covers 2026-08-10..2026-08-20 only:
            #   2026-08-12 Food (320)        →
            #   2026-08-15 Health (90)       →
            #   2026-08-20 Other (75)        →
            # Total = 485.00, 3 categories.
            breakdown = db_mod.get_category_breakdown_for_user(
                user_id,
                start_date="2026-08-10",
                end_date="2026-08-20",
            )

        assert sum(row["total"] for row in breakdown) == pytest.approx(485.0)
        categories = {row["category"] for row in breakdown}
        assert categories == {"Food", "Health", "Other"}

    def test_get_category_breakdown_no_bounds_regression(
        self, auth_client, app
    ):
        """No bounds: full breakdown (regression)."""
        with app.app_context():
            user_id = _get_demo_user_id()
            breakdown = db_mod.get_category_breakdown_for_user(user_id)

        assert sum(row["total"] for row in breakdown) == pytest.approx(
            EXPECTED_TOTAL
        )


# ===========================================================================
# Route tests on GET /profile with filter params
# ===========================================================================

class TestProfileRoute:

    def test_profile_unauthenticated_redirects(self, client):
        """Unauthenticated request with filter params → 302 to /login.

        Spec contract: "Unauthenticated requests to `GET /profile?range=this-month`
        still redirect to `/login`."
        """
        resp = client.get("/profile?range=this-month")
        assert resp.status_code == 302
        assert "/login" in (resp.headers.get("Location") or "")

    def test_profile_authenticated_this_month(self, auth_client, app):
        """Authenticated `?range=this-month` → 200 with month-scoped data.

        Spec contract: only seed expenses in the current month appear;
        totals reflect the filtered set; filter-bar markup present.
        """
        # We expect all 8 seed expenses to fall in August 2026.
        resp = auth_client.get("/profile?range=this-month")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")

        # Filter-bar markup present.
        assert 'class="filter-bar"' in body, (
            "Profile page must render the filter bar (class 'filter-bar')"
        )

        # Total = 250+60+1200+450+180+320+90+75 = 2625.00
        # The page formats it via format_inr → "₹2,625.00"
        assert "₹2,625.00" in body, (
            "Total spent should reflect the in-range sum (₹2,625.00). "
            "Body snippet: " + body[:500]
        )

        # The dropdown is keyed by URL `range=this-month` — value
        # attribute in the <select> options. Spec says preset label
        # "This month" should appear via the filter summary.
        assert "This month" in body or "This Month" in body, (
            "Active filter label 'This month' should be displayed."
        )

    def test_profile_authenticated_custom_range(self, auth_client):
        """Custom ?start=2026-08-10&end=2026-08-20 window."""
        resp = auth_client.get(
            "/profile?start=2026-08-10&end=2026-08-20"
        )
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")

        # Filtered total = 320 + 90 + 75 = 485.00
        assert "₹485.00" in body, (
            "Custom-range total should be ₹485.00. "
            "Body snippet: " + body[:500]
        )
        # Filter-bar present
        assert 'class="filter-bar"' in body

    def test_profile_authenticated_invalid_range_does_not_500(
        self, auth_client
    ):
        """`?range=garbage` must not 500 — page renders unfiltered."""
        resp = auth_client.get("/profile?range=garbage")
        assert resp.status_code == 200, (
            f"Invalid range must render a normal page; got {resp.status_code}"
        )
        # Behaves like unfiltered: full total of all 8 seed expenses.
        body = resp.data.decode("utf-8")
        assert "₹2,625.00" in body

    def test_profile_authenticated_invalid_start_falls_back(
        self, auth_client
    ):
        """`?start=garbage` falls back to the unfiltered view."""
        resp = auth_client.get("/profile?start=garbage")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "₹2,625.00" in body, (
            "Invalid start bound should fall back to the all-time view."
        )

    def test_profile_authenticated_no_query_shows_all(self, auth_client):
        """`GET /profile` (no query) — full history, 'All time' selected."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")

        # All 8 seed expenses → full total visible.
        assert "₹2,625.00" in body

        # The dropdown's "All time" option must be marked selected.
        # The template renders <option value="" ... selected> for it.
        assert (
            '<option value="" selected' in body
            or "selected>All time" in body
            or 'value="" selected' in body
        ), "Default state should mark 'All time' as the selected option."

    def test_profile_authenticated_this_month_has_clear_link(
        self, auth_client
    ):
        """`?range=this-month` shows a 'Clear' link pointing at /profile."""
        resp = auth_client.get("/profile?range=this-month")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")

        # The Clear control is a link to /profile (no query string).
        # Look for the word "Clear" near an href to /profile.
        assert "Clear" in body, "Filter bar must include a 'Clear' control."
        # Either an explicit /profile href (no query) or url_for('profile')
        # render — both must end up as href="/profile".
        assert 'href="/profile"' in body, (
            "Clear control should link to /profile (no query string)."
        )

    def test_profile_authenticated_empty_range_shows_empty_state(
        self, auth_client
    ):
        """Empty range: friendly empty-state copy on both sections."""
        resp = auth_client.get(
            "/profile?start=2020-01-01&end=2020-01-31"
        )
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")

        # Spec: "No transactions in this date range." (transaction table)
        # and "No expenses in this date range." (category breakdown).
        assert "No transactions in this date range" in body
        assert "No expenses in this date range" in body

    def test_profile_amounts_display_rupee(self, auth_client):
        """All amounts continue to display the ₹ symbol."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "₹" in body, "Profile page must render amounts with the ₹ symbol."

        # Also verify a filtered view still uses ₹
        resp2 = auth_client.get("/profile?range=this-month")
        assert resp2.status_code == 200
        body2 = resp2.data.decode("utf-8")
        assert "₹" in body2
