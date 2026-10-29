"""The month calendar and the year heatmap on a habit's page (no Flask, no SQL).

Both are lists of days with a "state" the template turns into a colour:
    done, partial (a count that's started), rest, missed, slipped (a habit
    to avoid), open (today, not done yet), off (not due that day),
    before (before the habit started), future
"""
import calendar
from datetime import date, timedelta

from .dates import add_months
from .schedule import is_due, week_start
from .streaks import start_of

WEEKS_IN_YEAR_GRID = 53
STATE_LABELS = {
    "done": "done", "partial": "started", "rest": "rest day", "missed": "not done",
    "slipped": "slipped", "open": "today", "off": "day off", "before": "before the start",
    "future": "",
}


def day_state(habit, day, sets, days, today):
    """What happened on one day. sets = (done, rest, slips) from daily.day_sets."""
    done, rest, slips = sets
    if day > today:
        return "future"
    if day < start_of(habit):
        return "before"
    if day in rest:
        return "rest"
    if day in slips:
        return "slipped"
    if day in done:
        return "done"  # done on a day off counts too: an extra
    if not is_due(habit, day):
        return "off"
    if day == today:
        return "open"
    if days.get(day, (0, 0))[0] > 0:
        return "partial"
    return "missed"


def level(habit, day, state, days):
    """How strong a heatmap square is, 0 to 4. A count habit fills up step by step."""
    if state == "done":
        return 4
    if state in ("partial", "open") and habit["kind"] == "count":
        share = days.get(day, (0, 0))[0] / habit["target"]
        return 3 if share >= 0.66 else 2 if share >= 0.33 else 1 if share > 0 else 0
    return 0


def cell(habit, day, sets, days, today):
    state = day_state(habit, day, sets, days, today)
    return {"day": day, "state": state, "level": level(habit, day, state, days),
            "value": days.get(day, (0, 0))[0], "label": STATE_LABELS[state]}


def month_grid(habit, sets, days, first, today):
    """The weeks of one month, Monday first: [[cell or None] * 7]. None = a day of another month."""
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month):
        weeks.append([cell(habit, day, sets, days, today) if day.month == first.month else None
                      for day in week])
    return weeks


def year_grid(habit, sets, days, today):
    """53 columns of weeks (oldest first), each Monday to Sunday, ending this week.

    Days after today are None. Also returns the month names to write above
    the columns: [(column, "Oct")], at each column where a new month starts.
    """
    first_monday = week_start(today) - timedelta(weeks=WEEKS_IN_YEAR_GRID - 1)
    columns, months = [], []
    for column in range(WEEKS_IN_YEAR_GRID):
        monday = first_monday + timedelta(weeks=column)
        columns.append([cell(habit, day, sets, days, today) if day <= today else None
                        for day in (monday + timedelta(days=i) for i in range(7))])
        if monday.day <= 7:
            months.append((column, f"{monday:%b}"))
    return columns, months


def monthly_totals(habit, done, today, months=12):
    """[(date of the 1st, days done)] for the last `months` months since the start, newest first."""
    first_month = today.replace(day=1)
    start = start_of(habit).replace(day=1)
    rows = []
    for back in range(months):
        month = add_months(first_month, -back)
        if month < start:
            break
        rows.append((month, sum(1 for day in done if (day.year, day.month) == (month.year, month.month))))
    return rows


def parse_month(text, today):
    """ "2026-10" -> date(2026, 10, 1); anything else (or a future month) -> this month."""
    try:
        first = date.fromisoformat(f"{text}-01")
    except (TypeError, ValueError):
        return today.replace(day=1)
    return min(first, today.replace(day=1))
