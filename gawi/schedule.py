"""When a habit is due, in plain Python (no Flask, no SQL).

A habit's schedule is one of:
- 'daily':    every day.
- 'weekdays': only on some days of the week. `weekdays` is text like "1,3,5"
              (Monday is 1 and Sunday is 7, like date.isoweekday()).
- 'weekly':   any `per_week` days a week (the week starts on Monday).
"""
from datetime import date, timedelta

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # index 0 is isoweekday 1


def weekday_numbers(text):
    """ "1,3,5" -> [1, 3, 5]."""
    return [int(part) for part in (text or "").split(",") if part.strip()]


def week_start(day):
    """The Monday of the week `day` is in. (weekday() is 0 on Monday.)"""
    return day - timedelta(days=day.weekday())


def is_due(habit, day):
    """Can this habit be done on this day, by its schedule?

    A 'weekly' habit can be done on any day; how many days are still
    needed this week is worked out elsewhere (daily.build_day).
    """
    if day < date.fromisoformat(habit["start_date"]):
        return False  # it hasn't started yet
    if habit["schedule"] == "weekdays":
        return day.isoweekday() in weekday_numbers(habit["weekdays"])
    return True


def describe(habit):
    """A short sentence for the schedule: "Every day", "Mon · Wed · Fri", "3 times a week"."""
    if habit["schedule"] == "weekdays":
        days = weekday_numbers(habit["weekdays"])
        if days == [1, 2, 3, 4, 5]:
            return "Weekdays"
        if days == [6, 7]:
            return "Weekends"
        return " · ".join(WEEKDAY_NAMES[day - 1] for day in days)
    if habit["schedule"] == "weekly":
        count = habit["per_week"]
        return "Once a week" if count == 1 else f"{count} times a week"
    return "Every day"


def goal(habit):
    """What "done" means for one day: "8 glasses", or "" for a yes/no habit."""
    if habit["kind"] != "count":
        return ""
    return f"{habit['target']} {habit['unit']}".strip()
