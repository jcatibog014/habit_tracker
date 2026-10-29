"""Small date helpers. Plain functions without Flask (see tests/test_dates.py).

Days are stored as text: "2026-10-28". Text in this ISO order sorts like
the dates themselves, so SQL can use <, >, BETWEEN and ORDER BY on it.

"Today" depends on where you are: at 7 AM in Manila it is still yesterday
in London. The live server's clock runs on UTC, so we never use
date.today(). We ask for the time in the user's time zone instead.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Asia/Manila"

# The time zones the Settings page offers: (name, label).
TIMEZONES = [
    ("Asia/Manila", "Philippines (Manila)"),
    ("Asia/Singapore", "Singapore"),
    ("Asia/Hong_Kong", "Hong Kong"),
    ("Asia/Tokyo", "Japan (Tokyo)"),
    ("Asia/Seoul", "South Korea (Seoul)"),
    ("Asia/Dubai", "United Arab Emirates (Dubai)"),
    ("Asia/Riyadh", "Saudi Arabia (Riyadh)"),
    ("Australia/Sydney", "Australia (Sydney)"),
    ("Europe/London", "United Kingdom (London)"),
    ("Europe/Rome", "Italy (Rome)"),
    ("America/New_York", "USA (New York)"),
    ("America/Chicago", "USA (Chicago)"),
    ("America/Los_Angeles", "USA (Los Angeles)"),
    ("America/Toronto", "Canada (Toronto)"),
    ("UTC", "UTC"),
]
TIMEZONE_NAMES = {name for name, _ in TIMEZONES}


def zone(name):
    """The ZoneInfo for a name, or the default one if the name is unknown."""
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def now(timezone_name=DEFAULT_TIMEZONE):
    return datetime.now(zone(timezone_name))


def today(timezone_name=DEFAULT_TIMEZONE):
    return now(timezone_name).date()


def parse_day(text):
    """ "2026-10-28" -> date(2026, 10, 28), or None if it isn't a day."""
    try:
        return date.fromisoformat(text or "")
    except ValueError:
        return None


def add_months(first_day, count):
    """Move the 1st of a month `count` months forward (or back, if negative)."""
    index = first_day.year * 12 + (first_day.month - 1) + count
    return date(index // 12, index % 12 + 1, 1)


def short_date(value, this_year=None):
    """ "2026-10-28" -> "Wed, Oct 28". Another year gets the year too: "Mon, Dec 29, 2025"."""
    day = date.fromisoformat(value) if isinstance(value, str) else value
    label = f"{day:%a}, {day:%b} {day.day}"  # day.day, because Windows has no %-d
    if day.year != (this_year or today().year):
        label += f", {day.year}"
    return label


def long_date(day):
    """date(2026, 10, 28) -> "Wednesday, October 28"."""
    return f"{day:%A}, {day:%B} {day.day}"
