from datetime import date, datetime, timezone

from gawi.dates import long_date, now, parse_day, short_date, today, zone
from gawi.schedule import describe, goal


def habit(**fields):
    return {"schedule": "daily", "weekdays": "", "per_week": None, "kind": "check",
            "target": 1, "unit": "", **fields}


def test_describe_the_schedule():
    assert describe(habit()) == "Every day"
    assert describe(habit(schedule="weekdays", weekdays="1,3,5")) == "Mon · Wed · Fri"
    assert describe(habit(schedule="weekdays", weekdays="1,2,3,4,5")) == "Weekdays"
    assert describe(habit(schedule="weekdays", weekdays="6,7")) == "Weekends"
    assert describe(habit(schedule="weekly", per_week=1)) == "Once a week"
    assert describe(habit(schedule="weekly", per_week=3)) == "3 times a week"


def test_goal():
    assert goal(habit()) == ""
    assert goal(habit(kind="count", target=8, unit="glasses")) == "8 glasses"
    assert goal(habit(kind="count", target=10000, unit="")) == "10000"


def test_today_depends_on_the_time_zone():
    # 20:00 UTC on Oct 28 is already Oct 29 in Manila (UTC+8), but still Oct 28 in New York.
    moment = datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc)
    assert moment.astimezone(zone("Asia/Manila")).date() == date(2026, 10, 29)
    assert moment.astimezone(zone("America/New_York")).date() == date(2026, 10, 28)
    assert today("Asia/Manila") == now("Asia/Manila").date()


def test_an_unknown_time_zone_falls_back_to_manila():
    assert zone("Mars/Base").key == "Asia/Manila"
    assert zone(None).key == "Asia/Manila"


def test_parse_day():
    assert parse_day("2026-02-28") == date(2026, 2, 28)
    assert parse_day("2026-02-30") is None
    assert parse_day("") is None and parse_day(None) is None


def test_short_and_long_dates():
    assert short_date("2026-10-28", this_year=2026) == "Wed, Oct 28"
    assert short_date("2025-12-29", this_year=2026) == "Mon, Dec 29, 2025"
    assert short_date(date(2026, 1, 5), this_year=2026) == "Mon, Jan 5"
    assert long_date(date(2026, 10, 28)) == "Wednesday, October 28"
