"""streaks.py with fixed dates: the rules for streaks, scores and milestones."""
from datetime import date, timedelta

import pytest

from gawi.daily import day_sets
from gawi.streaks import (
    completion, current_streak, earned, is_best_week, just_reached, longest_streak, next_milestone,
)

WEDNESDAY = date(2026, 10, 28)


def habit(**fields):
    return {"id": 1, "name": "H", "kind": "check", "target": 1, "unit": "", "avoid": 0,
            "schedule": "daily", "weekdays": "", "per_week": None, "start_date": "2026-01-01", **fields}


def days(*texts):
    return {date.fromisoformat(text) for text in texts}


def span(first, last):
    """Every day from first to last, as a set."""
    first, last = date.fromisoformat(first), date.fromisoformat(last)
    return {first + timedelta(days=n) for n in range((last - first).days + 1)}


@pytest.mark.parametrize("done, rest, expected", [
    # Today isn't done yet: the streak runs up to yesterday.
    (days("2026-10-25", "2026-10-26", "2026-10-27"), set(), 3),
    # Done today too: it counts.
    (days("2026-10-25", "2026-10-26", "2026-10-27", "2026-10-28"), set(), 4),
    # Missed yesterday: nothing yet (today is still open).
    (days("2026-10-25", "2026-10-26"), set(), 0),
    # A rest day doesn't break the streak, and doesn't add to it.
    (days("2026-10-24", "2026-10-25", "2026-10-27"), days("2026-10-26"), 3),
])
def test_daily_streaks(done, rest, expected):
    assert current_streak(habit(), done, rest, WEDNESDAY) == expected


def test_days_off_are_skipped():
    # Mon, Wed, Fri: Tuesdays and Thursdays don't break anything.
    mwf = habit(schedule="weekdays", weekdays="1,3,5")
    done = days("2026-10-21", "2026-10-23", "2026-10-26")  # Wed, Fri, Mon
    assert current_streak(mwf, done, set(), WEDNESDAY) == 3
    # Missing Friday breaks it.
    assert current_streak(mwf, days("2026-10-21", "2026-10-26"), set(), WEDNESDAY) == 1


def test_nothing_before_the_start_counts():
    new = habit(start_date="2026-10-27")
    assert current_streak(new, days("2026-10-27"), set(), WEDNESDAY) == 1
    assert current_streak(habit(start_date="2026-10-29"), set(), set(), WEDNESDAY) == 0
    assert longest_streak(habit(start_date="2026-10-29"), set(), set(), WEDNESDAY) == 0


def test_across_a_new_year_and_a_leap_day():
    done = days("2026-12-30", "2026-12-31", "2027-01-01")
    assert current_streak(habit(), done, set(), date(2027, 1, 2)) == 3
    done = days("2028-02-28", "2028-02-29", "2028-03-01")
    assert current_streak(habit(), done, set(), date(2028, 3, 2)) == 3


def test_longest_streak():
    done = span("2026-10-01", "2026-10-10") | span("2026-10-12", "2026-10-14")
    assert longest_streak(habit(start_date="2026-10-01"), done, set(), WEDNESDAY) == 10
    # Today not being done yet doesn't cut the longest run either.
    done = span("2026-10-20", "2026-10-27")
    assert longest_streak(habit(start_date="2026-10-01"), done, set(), WEDNESDAY) == 8


def test_weekly_habits_count_in_weeks():
    twice = habit(schedule="weekly", per_week=2, start_date="2026-10-05")
    done = days("2026-10-06", "2026-10-08",   # week of Oct 5
                "2026-10-13", "2026-10-16",   # week of Oct 12
                "2026-10-20", "2026-10-25")   # week of Oct 19
    # This week (Oct 26) isn't reached yet, but it doesn't break the streak.
    assert current_streak(twice, done, set(), WEDNESDAY) == 3
    assert current_streak(twice, done | days("2026-10-26", "2026-10-27"), set(), WEDNESDAY) == 4
    # A week with only one day breaks it...
    assert current_streak(twice, done - days("2026-10-16"), set(), WEDNESDAY) == 1
    # ...unless a rest day makes up the difference.
    assert current_streak(twice, done - days("2026-10-16"), days("2026-10-17"), WEDNESDAY) == 3
    assert longest_streak(twice, done - days("2026-10-16"), set(), WEDNESDAY) == 1


def test_a_first_short_week_needs_fewer_days():
    # Starts on a Saturday: that first week only has 2 days, so 2 are enough for "3 times a week".
    three = habit(schedule="weekly", per_week=3, start_date="2026-10-17")
    done = days("2026-10-17", "2026-10-18", "2026-10-19", "2026-10-21", "2026-10-23")
    assert current_streak(three, done, set(), WEDNESDAY) == 2


def test_a_habit_to_avoid():
    soda = habit(avoid=1, start_date="2026-10-20")
    done, rest, _ = day_sets(soda, {date(2026, 10, 24): (1, 0)}, WEDNESDAY)  # a slip on the 24th
    assert current_streak(soda, done, rest, WEDNESDAY) == 4  # the 25th to today (clean so far)
    assert longest_streak(soda, done, rest, WEDNESDAY) == 4
    # A slip today has already happened: it ends the streak (today isn't "still open").
    done, rest, _ = day_sets(soda, {WEDNESDAY: (1, 0)}, WEDNESDAY)
    assert current_streak(soda, done, rest, WEDNESDAY) == 0
    assert longest_streak(soda, done, rest, WEDNESDAY) == 8  # the 20th to the 27th


def test_completion_leaves_out_rest_days_and_an_open_today():
    h = habit(start_date="2026-10-01")
    done = span("2026-10-01", "2026-10-20")       # 20 of the 27 days before today
    assert completion(h, done, set(), date(2026, 10, 1), WEDNESDAY) == 74
    rest = days("2026-10-21", "2026-10-22")       # 2 rest days: 20 of 25
    assert completion(h, done, rest, date(2026, 10, 1), WEDNESDAY) == 80
    assert completion(habit(start_date="2026-10-29"), set(), set(), date(2026, 10, 1), WEDNESDAY) is None


def test_weekly_completion_counts_weeks():
    twice = habit(schedule="weekly", per_week=2, start_date="2026-10-05")
    done = days("2026-10-06", "2026-10-08", "2026-10-13")  # week 1 reached, week 2 not, week 3 not
    # Weeks of Oct 5, 12, 19 are finished; this week is still going and not reached yet.
    assert completion(twice, done, set(), date(2026, 10, 1), WEDNESDAY) == 33


def test_milestones():
    day = habit()
    assert earned(day, 34) == [7, 30]
    assert next_milestone(day, 34) == 100 and next_milestone(day, 400) is None
    assert just_reached(day, 29, 30) == 30
    assert just_reached(day, 30, 30) is None and just_reached(day, 30, 31) is None
    weekly = habit(schedule="weekly", per_week=2)
    assert earned(weekly, 5) == [4] and just_reached(weekly, 11, 12) == 12


def test_best_week_ever():
    mondays = [date(2026, 10, 5), date(2026, 10, 12), date(2026, 10, 19), date(2026, 10, 26)]
    assert is_best_week({mondays[0]: 10, mondays[1]: 12, mondays[3]: 13}, mondays[3])
    assert not is_best_week({mondays[0]: 10, mondays[1]: 13, mondays[3]: 13}, mondays[3])  # a tie isn't a record
    assert not is_best_week({mondays[2]: 1, mondays[3]: 5}, mondays[3])  # too new to compare
