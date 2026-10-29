"""Streaks, scores and milestones, in plain Python (no Flask, no SQL).

Every function takes the facts as sets of dates, so tests can use any day:
    done  the days the habit was done (for a habit to avoid: the days
          without a slip, see daily.day_sets)
    rest  rest days: they never break a streak and never add to one
    today the user's today

The rules:
- A day habit (every day, some weekdays, avoid) counts in days. Days it
  isn't due are ignored, so Mon/Wed/Fri goes Fri -> Wed -> Mon.
- Today isn't over: if it isn't done yet, the streak runs up to yesterday.
- A "3 times a week" habit counts in weeks (Monday to Sunday). A week
  counts when done days + rest days reach the goal. The current week adds
  one once it's reached, and never breaks the streak while it's going.
- Nothing before the habit's start date counts.
"""
from datetime import date, timedelta

from .schedule import is_due, week_start

ONE_DAY = timedelta(days=1)
ONE_WEEK = timedelta(days=7)

# The streak lengths that earn a badge.
MILESTONES = {"days": [7, 30, 100, 365], "weeks": [4, 12, 26, 52]}


def unit(habit):
    """ "weeks" for a "some times a week" habit, else "days"."""
    return "weeks" if habit["schedule"] == "weekly" else "days"


def start_of(habit):
    return date.fromisoformat(habit["start_date"])


# ---------- Day habits ----------

def _still_open(habit, day, today):
    """Today isn't over, so not having done it yet isn't a miss.
    For a habit to avoid it's different: a slip today has already happened."""
    return day == today and not habit.get("avoid")


def _current_days(habit, done, rest, today):
    count, day, start = 0, today, start_of(habit)
    while day >= start:
        if is_due(habit, day):
            if day in done:
                count += 1
            elif day in rest or _still_open(habit, day, today):
                pass  # a rest day, or today, which isn't over yet
            else:
                break  # a missed day (or a slip) ends the streak
        day -= ONE_DAY
    return count


def _longest_days(habit, done, rest, today):
    best = run = 0
    day = start_of(habit)
    while day <= today:
        if is_due(habit, day):
            if day in done:
                run += 1
                best = max(best, run)
            elif day not in rest and not _still_open(habit, day, today):
                run = 0
        day += ONE_DAY
    return best


# ---------- Week habits ----------

def _week_needs(habit, monday):
    """How many days this week needs. A habit that starts mid-week only
    needs as many as there were days left in its first week."""
    days_in_week = (monday + timedelta(days=6) - max(monday, start_of(habit))).days + 1
    return min(habit["per_week"], days_in_week)


def _week_reached(habit, done, rest, monday):
    days = [monday + timedelta(days=i) for i in range(7)]
    got = sum(1 for day in days if day in done or day in rest)
    return got >= _week_needs(habit, monday)


def _first_monday(habit):
    return week_start(start_of(habit))


def _current_weeks(habit, done, rest, today):
    this_monday = week_start(today)
    count = 1 if _week_reached(habit, done, rest, this_monday) else 0
    monday = this_monday - ONE_WEEK
    while monday >= _first_monday(habit):
        if not _week_reached(habit, done, rest, monday):
            break
        count += 1
        monday -= ONE_WEEK
    return count


def _longest_weeks(habit, done, rest, today):
    best = run = 0
    monday, this_monday = _first_monday(habit), week_start(today)
    while monday <= this_monday:
        if _week_reached(habit, done, rest, monday):
            run += 1
            best = max(best, run)
        elif monday != this_monday:  # the current week can still be reached
            run = 0
        monday += ONE_WEEK
    return best


# ---------- Both ----------

def current_streak(habit, done, rest, today):
    """How many days (or weeks) in a row, up to now."""
    if today < start_of(habit):
        return 0
    if unit(habit) == "weeks":
        return _current_weeks(habit, done, rest, today)
    return _current_days(habit, done, rest, today)


def longest_streak(habit, done, rest, today):
    """The best streak ever, up to now."""
    if today < start_of(habit):
        return 0
    if unit(habit) == "weeks":
        return _longest_weeks(habit, done, rest, today)
    return _longest_days(habit, done, rest, today)


def completion(habit, done, rest, first, today):
    """The percent done from `first` to today, or None if nothing was due.

    Rest days don't count at all, and today only counts once it's done
    (it isn't over yet). A weekly habit is scored by its finished weeks:
    3 of 4 weeks reached is 75%.
    """
    first = max(first, start_of(habit))
    if unit(habit) == "weeks":
        weeks = reached = 0
        monday = week_start(first)
        while monday <= week_start(today):
            ok = _week_reached(habit, done, rest, monday)
            if monday != week_start(today) or ok:
                weeks += 1
                reached += ok
            monday += ONE_WEEK
        return round(100 * reached / weeks) if weeks else None

    due = hit = 0
    day = first
    while day <= today:
        if is_due(habit, day) and day not in rest and (day != today or day in done):
            due += 1
            hit += day in done
        day += ONE_DAY
    return round(100 * hit / due) if due else None


# ---------- Milestones ----------

def earned(habit, best):
    """The badges a best streak of `best` has earned: [7, 30] for 34 days."""
    return [m for m in MILESTONES[unit(habit)] if m <= best]


def next_milestone(habit, streak):
    """The next badge to aim for, or None after the last one."""
    return next((m for m in MILESTONES[unit(habit)] if m > streak), None)


def just_reached(habit, before, after):
    """The milestone a tick just reached (the streak went from 29 to 30), or None."""
    if after > before and after in MILESTONES[unit(habit)]:
        return after
    return None


# ---------- Weeks of all habits ----------

def is_best_week(done_by_week, this_monday):
    """Is this week the best one yet? done_by_week: {monday: days done, all habits}.

    It needs at least two earlier weeks to beat, so a brand-new user
    doesn't get "best week ever" on day one.
    """
    this_week = done_by_week.get(this_monday, 0)
    earlier = [count for monday, count in done_by_week.items() if monday < this_monday]
    return len(earlier) >= 2 and this_week > max(earlier)
