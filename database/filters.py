"""Date-filter resolver for the /profile page.

Pure helpers — no Flask imports. The route passes the raw query-arg dict
and gets back a normalised filter payload the template can render.
"""
from datetime import date, datetime, timedelta


# ---- Presets ---------------------------------------------------------------
# Each preset is a callable: today -> (start_iso, end_iso). Keeping them as
# callables (not static tuples) means tests can pin "today" and the presets
# stay rolling in production.

def _this_month(today):
    start = today.replace(day=1)
    # First day of next month, minus one day = last day of this month.
    if today.month == 12:
        next_month_first = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_first = today.replace(month=today.month + 1, day=1)
    end = next_month_first - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _last_month(today):
    first_this_month = today.replace(day=1)
    last_day_prev = first_this_month - timedelta(days=1)
    start = last_day_prev.replace(day=1)
    return start.isoformat(), last_day_prev.isoformat()


def _last_n(n):
    def fn(today):
        start = today - timedelta(days=n - 1)
        return start.isoformat(), today.isoformat()
    fn.__name__ = f"_last_{n}"
    return fn


def _ytd(today):
    return today.replace(month=1, day=1).isoformat(), today.isoformat()


PRESETS = {
    "this-month": _this_month,
    "last-month": _last_month,
    "last-30":    _last_n(30),
    "last-90":    _last_n(90),
    "ytd":        _ytd,
}


# ---- Preset labels ---------------------------------------------------------

PRESET_LABELS = {
    "this-month": "This month",
    "last-month": "Last month",
    "last-30":    "Last 30 days",
    "last-90":    "Last 90 days",
    "ytd":        "Year to date",
}


# ---- Date validation -------------------------------------------------------

def _is_iso_date(s):
    """True if s is a YYYY-MM-DD string that datetime can parse."""
    if not s or not isinstance(s, str):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _format_range_label(start, end):
    """Render '01 Aug 2026 — 31 Aug 2026' from two ISO date strings."""
    s = datetime.strptime(start, "%Y-%m-%d").strftime("%d %b %Y")
    e = datetime.strptime(end, "%Y-%m-%d").strftime("%d %b %Y")
    return f"{s} — {e}"


# ---- Public API ------------------------------------------------------------

def resolve_filter(args, today=None):
    """Resolve a query-arg dict into a filter payload for /profile.

    args keys (all optional): 'range', 'start', 'end'.

    Returns a dict:
        start, end : ISO YYYY-MM-DD strings or None
        preset     : preset key string or None (the *currently active* preset)
        label      : human-readable summary, e.g. "This month" or
                     "01 Aug 2026 — 31 Aug 2026" or "All time"
        active     : bool, True if any filter is applied

    Rules (per spec):
      - Invalid start/end values silently fall back to None (no 400).
      - When a valid preset is in the URL, the preset is authoritative:
        its computed dates override any start/end the browser resubmitted.
        This avoids the stale-date-pickers trap where picking a new preset
        from the dropdown silently kept the previous preset's range.
      - When no preset is in the URL, explicit start/end (if both valid)
        define the applied filter — for a custom range without a preset.
      - The currently-active preset (per the URL) is what the dropdown's
        `selected` attribute reflects.
      - `today` is injectable for tests; defaults to date.today().
    """
    today = today or date.today()

    raw_range = (args.get("range") or "").strip() or None
    raw_start = (args.get("start") or "").strip() or None
    raw_end   = (args.get("end") or "").strip() or None

    # Validate. Invalid values -> None, never raise.
    start = raw_start if _is_iso_date(raw_start) else None
    end   = raw_end   if _is_iso_date(raw_end)   else None

    # `preset` for the dropdown: take from URL if it's a known preset.
    preset = raw_range if raw_range in PRESETS else None

    # Decide what filter is actually applied.
    # When a preset is explicitly named in the URL, the preset is
    # authoritative — recompute its dates and use those. This handles the
    # case where the browser resubmits stale start/end from the date
    # pickers (which still show the previous preset's dates until the
    # response re-renders them). Without this, picking a new preset would
    # silently be ignored if the previous preset had populated the pickers.
    applied_start, applied_end = start, end
    if preset is not None:
        applied_start, applied_end = PRESETS[preset](today)

    # Build the label.
    if applied_start is not None and applied_end is not None:
        if preset is not None and preset in PRESET_LABELS:
            label = PRESET_LABELS[preset]
        else:
            label = _format_range_label(applied_start, applied_end)
    elif applied_start is not None:
        label = f"From {datetime.strptime(applied_start, '%Y-%m-%d').strftime('%d %b %Y')}"
    elif applied_end is not None:
        label = f"Up to {datetime.strptime(applied_end, '%Y-%m-%d').strftime('%d %b %Y')}"
    else:
        label = "All time"

    return {
        "start":  applied_start,
        "end":    applied_end,
        "preset": preset,
        "label":  label,
        "active": (applied_start is not None) or (applied_end is not None),
    }
