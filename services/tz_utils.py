"""
Storage convention: every datetime in the database is naive (no tzinfo)
and represents UTC. This module is the only place that should convert
between that and a field's local wall-clock time.

Why UTC-only storage: comparisons, scheduling math, and "how long ago"
calculations are all correct without extra work if everything in the
DB is already the same timezone. Local time only matters at the two
edges — when a person types a time in, and when we show one on screen.
"""

import pytz
from datetime import datetime

DEFAULT_TIMEZONE = "America/Chicago"

# A curated list for the dropdown, not all ~400 pytz zones — mostly US,
# plus a few common international ones so the field isn't US-only.
COMMON_TIMEZONES = [
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Phoenix",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Madrid",
    "Africa/Cairo",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Australia/Sydney",
]


def is_valid_timezone(tz_name):
    return tz_name in pytz.all_timezones_set


def local_naive_to_utc_naive(naive_local_dt, tz_name):
    """
    Takes a naive datetime representing wall-clock time in tz_name
    (exactly what an <input type="datetime-local"> gives you) and
    returns a naive datetime representing the same instant in UTC —
    the form everything is stored in.
    """
    if naive_local_dt is None:
        return None
    tz = pytz.timezone(tz_name)
    localized = tz.localize(naive_local_dt)
    utc_dt = localized.astimezone(pytz.UTC)
    return utc_dt.replace(tzinfo=None)


def utc_naive_to_local_iso(naive_utc_dt, tz_name):
    """
    Takes a naive datetime known to represent UTC (our storage
    convention) and returns an ISO 8601 string localized to tz_name,
    with the UTC offset included, for display only.
    """
    if naive_utc_dt is None:
        return None
    utc_dt = pytz.UTC.localize(naive_utc_dt)
    tz = pytz.timezone(tz_name)
    local_dt = utc_dt.astimezone(tz)
    return local_dt.isoformat()
